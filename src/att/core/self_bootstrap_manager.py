"""Self-bootstrap workflow manager."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from att.core.git_manager import GitManager
from att.core.tool_orchestrator import ToolOrchestrator, WorkflowRunResult
from att.db.store import SQLiteStore
from att.models.events import ATTEvent, EventType

type CIStatus = Literal["pending", "success", "failure"]
type CIChecker = Callable[[str, str], Awaitable[CIStatus]]
type HealthChecker = Callable[[str], Awaitable[bool]]
type Sleeper = Callable[[float], Awaitable[None]]
type PRCreator = Callable[[str, str], Awaitable[str]]
type PRMerger = Callable[[str, str], Awaitable[bool]]
type Deployer = Callable[[str, str], Awaitable[bool]]
type RollbackExecutorLegacy = Callable[[str, str], Awaitable[bool]]
type RollbackExecutorWithRelease = Callable[[str, str, str | None], Awaitable[bool]]
type RollbackExecutor = RollbackExecutorLegacy | RollbackExecutorWithRelease


@dataclass(slots=True)
class RestartWatchdogSignal:
    """Runtime restart watchdog check output."""

    stable: bool
    reason: str | None = None
    probe: str = "process"


type RestartWatchdog = Callable[[str, str], Awaitable[RestartWatchdogSignal | bool]]


@dataclass(slots=True)
class ReleaseMetadata:
    """Release metadata resolved from a concrete source."""

    current_release_id: str | None
    previous_release_id: str | None
    source: str


type ReleaseMetadataProvider = Callable[[str, Path], Awaitable[ReleaseMetadata | None]]


@dataclass(slots=True)
class SelfBootstrapRequest:
    """Input payload for a self-bootstrap cycle."""

    project_id: str
    project_path: Path
    file_path: str
    content: str
    commit_message: str
    suite: str = "unit"
    branch_name: str | None = None
    ci_timeout_seconds: int = 600
    ci_initial_poll_seconds: int = 10
    ci_max_poll_seconds: int = 60
    create_pr: bool = True
    auto_merge_on_ci_success: bool = True
    deploy_target: str | None = None
    requested_release_id: str | None = None
    previous_release_id: str | None = None
    rollback_release_id: str | None = None
    health_check_target: str | None = None
    health_check_retries: int = 1
    health_check_interval_seconds: int = 5
    restart_watchdog_retries: int = 3
    restart_watchdog_interval_seconds: int = 5


@dataclass(slots=True)
class SelfBootstrapResult:
    """Output summary for a self-bootstrap cycle."""

    branch_name: str
    committed: bool
    pushed: bool
    ci_status: str
    pr_url: str | None
    merged: bool
    restart_watchdog_status: str
    health_status: str
    rollback_performed: bool
    rollback_succeeded: bool | None
    success: bool
    workflow_result: WorkflowRunResult
    restart_watchdog_reason: str | None = None
    deployed_release_id: str | None = None
    rollback_target_release_id: str | None = None
    release_metadata_source: str | None = None


class SelfBootstrapManager:
    """Coordinate branch, change, CI, merge, deploy, and health checks."""

    def __init__(
        self,
        *,
        git_manager: GitManager,
        orchestrator: ToolOrchestrator,
        store: SQLiteStore,
        ci_checker: CIChecker | None = None,
        health_checker: HealthChecker | None = None,
        pr_creator: PRCreator | None = None,
        pr_merger: PRMerger | None = None,
        deployer: Deployer | None = None,
        restart_watchdog: RestartWatchdog | None = None,
        rollback_executor: RollbackExecutor | None = None,
        release_metadata_provider: ReleaseMetadataProvider | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._git = git_manager
        self._orchestrator = orchestrator
        self._store = store
        self._ci_checker = ci_checker
        self._health_checker = health_checker
        self._pr_creator = pr_creator
        self._pr_merger = pr_merger
        self._deployer = deployer
        self._restart_watchdog = restart_watchdog
        self._rollback_executor = rollback_executor
        self._release_metadata_provider = release_metadata_provider
        self._sleep = sleeper or asyncio.sleep

    async def execute(self, request: SelfBootstrapRequest) -> SelfBootstrapResult:
        """Run a baseline self-bootstrap cycle."""
        release_metadata = await self._resolve_release_metadata(request)
        branch_name = request.branch_name or f"codex/self-bootstrap-{uuid4().hex[:8]}"
        pr_url: str | None = None
        merged = False
        restart_watchdog_status = "not_run"
        restart_watchdog_reason: str | None = None
        deployed_release_id = request.requested_release_id or (
            release_metadata.current_release_id if release_metadata is not None else None
        )
        rollback_target_release_id = self._resolve_rollback_release_id(request, release_metadata)
        release_metadata_source = release_metadata.source if release_metadata is not None else None

        self._git.branch(request.project_path, branch_name, checkout=True)

        workflow = await self._orchestrator.run_change_workflow(
            project_id=request.project_id,
            project_path=request.project_path,
            rel_path=request.file_path,
            new_content=request.content,
            suite=request.suite,
            commit_message=request.commit_message,
        )

        if not workflow.committed:
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.ERROR,
                payload={"phase": "commit", "message": "Commit skipped because tests failed"},
            )
            return SelfBootstrapResult(
                branch_name=branch_name,
                committed=False,
                pushed=False,
                ci_status="not_run",
                pr_url=None,
                merged=False,
                restart_watchdog_status=restart_watchdog_status,
                health_status="not_run",
                rollback_performed=False,
                rollback_succeeded=None,
                success=False,
                workflow_result=workflow,
                release_metadata_source=release_metadata_source,
            )

        self._git.push(request.project_path, "origin", branch_name)

        if request.create_pr and self._pr_creator is not None:
            pr_url = await self._pr_creator(request.project_id, branch_name)
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.GIT_PR_CREATED,
                payload={"branch": branch_name, "url": pr_url},
            )

        ci_status = "not_run"
        if self._ci_checker is not None:
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.BUILD_STARTED,
                payload={"branch": branch_name},
            )
            ci_status = await self._poll_ci(
                project_id=request.project_id,
                branch_name=branch_name,
                timeout_seconds=request.ci_timeout_seconds,
                initial_poll_seconds=request.ci_initial_poll_seconds,
                max_poll_seconds=request.ci_max_poll_seconds,
            )
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.BUILD_COMPLETED,
                payload={"branch": branch_name, "status": ci_status},
            )
            if ci_status != "success":
                return SelfBootstrapResult(
                    branch_name=branch_name,
                    committed=True,
                    pushed=True,
                    ci_status=ci_status,
                    pr_url=pr_url,
                    merged=False,
                    restart_watchdog_status=restart_watchdog_status,
                    health_status="not_run",
                    rollback_performed=False,
                    rollback_succeeded=None,
                    success=False,
                    workflow_result=workflow,
                    deployed_release_id=deployed_release_id,
                    rollback_target_release_id=rollback_target_release_id,
                    release_metadata_source=release_metadata_source,
                )

        if request.auto_merge_on_ci_success and pr_url is not None and self._pr_merger is not None:
            merged = await self._pr_merger(request.project_id, pr_url)
            if merged:
                await self._record_event(
                    project_id=request.project_id,
                    event_type=EventType.GIT_PR_MERGED,
                    payload={"url": pr_url},
                )
            else:
                await self._record_event(
                    project_id=request.project_id,
                    event_type=EventType.ERROR,
                    payload={"phase": "merge", "url": pr_url, "message": "PR merge failed"},
                )
                return SelfBootstrapResult(
                    branch_name=branch_name,
                    committed=True,
                    pushed=True,
                    ci_status=ci_status,
                    pr_url=pr_url,
                    merged=False,
                    restart_watchdog_status=restart_watchdog_status,
                    health_status="not_run",
                    rollback_performed=False,
                    rollback_succeeded=None,
                    success=False,
                    workflow_result=workflow,
                    deployed_release_id=deployed_release_id,
                    rollback_target_release_id=rollback_target_release_id,
                    release_metadata_source=release_metadata_source,
                )

        health_status = "not_run"
        rollback_performed = False
        rollback_succeeded: bool | None = None
        deploy_target = request.deploy_target or request.health_check_target

        if self._deployer is not None and deploy_target is not None:
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.DEPLOY_STARTED,
                payload={
                    "target": deploy_target,
                    "release_id": deployed_release_id,
                },
            )
            deployed = await self._deployer(request.project_id, deploy_target)
            if not deployed:
                await self._record_event(
                    project_id=request.project_id,
                    event_type=EventType.ERROR,
                    payload={
                        "phase": "deploy",
                        "target": deploy_target,
                        "release_id": deployed_release_id,
                        "message": "Deploy failed",
                    },
                )
                await self._record_event(
                    project_id=request.project_id,
                    event_type=EventType.DEPLOY_COMPLETED,
                    payload={
                        "target": deploy_target,
                        "healthy": False,
                        "release_id": deployed_release_id,
                    },
                )
                return SelfBootstrapResult(
                    branch_name=branch_name,
                    committed=True,
                    pushed=True,
                    ci_status=ci_status,
                    pr_url=pr_url,
                    merged=merged,
                    restart_watchdog_status=restart_watchdog_status,
                    health_status="not_run",
                    rollback_performed=False,
                    rollback_succeeded=None,
                    success=False,
                    workflow_result=workflow,
                )

        if self._restart_watchdog is not None and deploy_target is not None:
            restart_signal = await self._poll_restart_watchdog(
                project_id=request.project_id,
                target=deploy_target,
                retries=request.restart_watchdog_retries,
                interval_seconds=request.restart_watchdog_interval_seconds,
            )
            restart_watchdog_status = "stable" if restart_signal.stable else "unstable"
            restart_watchdog_reason = restart_signal.reason
            if not restart_signal.stable:
                await self._record_event(
                    project_id=request.project_id,
                    event_type=EventType.ERROR,
                    payload={
                        "phase": "restart_watchdog",
                        "target": deploy_target,
                        "release_id": deployed_release_id,
                        "message": restart_signal.reason
                        or "Runtime failed restart watchdog checks",
                    },
                )
                rollback_performed, rollback_succeeded = await self._attempt_rollback(
                    project_id=request.project_id,
                    target=deploy_target,
                    target_release_id=rollback_target_release_id,
                )
                await self._record_event(
                    project_id=request.project_id,
                    event_type=EventType.DEPLOY_COMPLETED,
                    payload={
                        "target": deploy_target,
                        "healthy": False,
                        "release_id": deployed_release_id,
                        "restart_watchdog_status": restart_watchdog_status,
                        "restart_watchdog_reason": restart_watchdog_reason,
                        "rollback_target_release_id": rollback_target_release_id,
                    },
                )
                return SelfBootstrapResult(
                    branch_name=branch_name,
                    committed=True,
                    pushed=True,
                    ci_status=ci_status,
                    pr_url=pr_url,
                    merged=merged,
                    restart_watchdog_status=restart_watchdog_status,
                    health_status="not_run",
                    rollback_performed=rollback_performed,
                    rollback_succeeded=rollback_succeeded,
                    success=False,
                    workflow_result=workflow,
                    restart_watchdog_reason=restart_watchdog_reason,
                    deployed_release_id=deployed_release_id,
                    rollback_target_release_id=rollback_target_release_id,
                    release_metadata_source=release_metadata_source,
                )

        if self._health_checker is not None and request.health_check_target is not None:
            healthy = await self._poll_health(
                target=request.health_check_target,
                retries=request.health_check_retries,
                interval_seconds=request.health_check_interval_seconds,
            )
            health_status = "healthy" if healthy else "unhealthy"
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.DEPLOY_COMPLETED,
                payload={
                    "target": request.health_check_target,
                    "healthy": healthy,
                    "release_id": deployed_release_id,
                    "restart_watchdog_status": restart_watchdog_status,
                    "restart_watchdog_reason": restart_watchdog_reason,
                },
            )
            if not healthy:
                if deploy_target is not None:
                    rollback_performed, rollback_succeeded = await self._attempt_rollback(
                        project_id=request.project_id,
                        target=deploy_target,
                        target_release_id=rollback_target_release_id,
                    )

                return SelfBootstrapResult(
                    branch_name=branch_name,
                    committed=True,
                    pushed=True,
                    ci_status=ci_status,
                    pr_url=pr_url,
                    merged=merged,
                    restart_watchdog_status=restart_watchdog_status,
                    health_status=health_status,
                    rollback_performed=rollback_performed,
                    rollback_succeeded=rollback_succeeded,
                    success=False,
                    workflow_result=workflow,
                    restart_watchdog_reason=restart_watchdog_reason,
                    deployed_release_id=deployed_release_id,
                    rollback_target_release_id=rollback_target_release_id,
                    release_metadata_source=release_metadata_source,
                )

        if deploy_target is not None and not (
            self._health_checker is not None and request.health_check_target is not None
        ):
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.DEPLOY_COMPLETED,
                payload={
                    "target": deploy_target,
                    "healthy": True,
                    "release_id": deployed_release_id,
                    "restart_watchdog_status": restart_watchdog_status,
                    "restart_watchdog_reason": restart_watchdog_reason,
                },
            )

        return SelfBootstrapResult(
            branch_name=branch_name,
            committed=True,
            pushed=True,
            ci_status=ci_status,
            pr_url=pr_url,
            merged=merged,
            restart_watchdog_status=restart_watchdog_status,
            health_status=health_status,
            rollback_performed=rollback_performed,
            rollback_succeeded=rollback_succeeded,
            success=True,
            workflow_result=workflow,
            restart_watchdog_reason=restart_watchdog_reason,
            deployed_release_id=deployed_release_id,
            rollback_target_release_id=rollback_target_release_id,
            release_metadata_source=release_metadata_source,
        )

    async def _attempt_rollback(
        self,
        *,
        project_id: str,
        target: str,
        target_release_id: str | None,
    ) -> tuple[bool, bool | None]:
        if self._rollback_executor is None:
            return False, None
        rollback_succeeded = await self._run_rollback_executor(
            project_id=project_id,
            target=target,
            target_release_id=target_release_id,
        )
        await self._record_event(
            project_id=project_id,
            event_type=EventType.ERROR,
            payload={
                "phase": "rollback",
                "target": target,
                "succeeded": rollback_succeeded,
                "release_id": target_release_id,
            },
        )
        return True, rollback_succeeded

    @staticmethod
    def _resolve_rollback_release_id(
        request: SelfBootstrapRequest,
        release_metadata: ReleaseMetadata | None,
    ) -> str | None:
        if request.rollback_release_id:
            return request.rollback_release_id
        if request.previous_release_id:
            return request.previous_release_id
        if release_metadata is not None:
            return release_metadata.previous_release_id
        return None

    async def _resolve_release_metadata(
        self,
        request: SelfBootstrapRequest,
    ) -> ReleaseMetadata | None:
        if self._release_metadata_provider is None:
            return None
        if request.requested_release_id is not None and request.previous_release_id is not None:
            return None
        return await self._release_metadata_provider(request.project_id, request.project_path)

    async def _run_rollback_executor(
        self,
        *,
        project_id: str,
        target: str,
        target_release_id: str | None,
    ) -> bool:
        if self._rollback_executor is None:
            return False
        if self._rollback_executor_accepts_release_id(self._rollback_executor):
            executor_with_release = cast(RollbackExecutorWithRelease, self._rollback_executor)
            return await executor_with_release(project_id, target, target_release_id)
        executor_legacy = cast(RollbackExecutorLegacy, self._rollback_executor)
        return await executor_legacy(project_id, target)

    @staticmethod
    def _rollback_executor_accepts_release_id(executor: RollbackExecutor) -> bool:
        try:
            signature = inspect.signature(executor)
        except (TypeError, ValueError):
            return False
        positional_params = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        return len(positional_params) >= 3

    async def _poll_health(
        self,
        *,
        target: str,
        retries: int,
        interval_seconds: int,
    ) -> bool:
        attempts = max(1, retries)
        for attempt in range(attempts):
            if self._health_checker is None:
                return True
            healthy = await self._health_checker(target)
            if healthy:
                return True
            if attempt < attempts - 1:
                await self._sleep(float(interval_seconds))
        return False

    async def _poll_restart_watchdog(
        self,
        *,
        project_id: str,
        target: str,
        retries: int,
        interval_seconds: int,
    ) -> RestartWatchdogSignal:
        attempts = max(1, retries)
        last_signal = RestartWatchdogSignal(stable=False, reason="Runtime restart watchdog failed")
        for attempt in range(attempts):
            if self._restart_watchdog is None:
                return RestartWatchdogSignal(stable=True, reason="watchdog_not_configured")
            raw_signal = await self._restart_watchdog(project_id, target)
            signal = self._coerce_restart_watchdog_signal(raw_signal)
            if signal.stable:
                return signal
            last_signal = signal
            if attempt < attempts - 1:
                await self._sleep(float(interval_seconds))
        return last_signal

    @staticmethod
    def _coerce_restart_watchdog_signal(
        signal: RestartWatchdogSignal | bool,
    ) -> RestartWatchdogSignal:
        if isinstance(signal, RestartWatchdogSignal):
            return signal
        return RestartWatchdogSignal(
            stable=signal,
            reason="runtime_healthy" if signal else "runtime_unhealthy",
        )

    async def _poll_ci(
        self,
        *,
        project_id: str,
        branch_name: str,
        timeout_seconds: int,
        initial_poll_seconds: int,
        max_poll_seconds: int,
    ) -> str:
        if self._ci_checker is None:
            return "not_run"

        started = datetime.now(UTC)
        wait_seconds = float(initial_poll_seconds)

        while True:
            status = await self._ci_checker(project_id, branch_name)
            if status == "success":
                return "success"
            if status == "failure":
                return "failure"

            elapsed = (datetime.now(UTC) - started).total_seconds()
            if elapsed >= timeout_seconds:
                return "timeout"

            await self._sleep(wait_seconds)
            wait_seconds = min(wait_seconds * 2, float(max_poll_seconds))

    async def _record_event(
        self,
        *,
        project_id: str,
        event_type: EventType,
        payload: dict[str, str | int | float | bool | None],
    ) -> None:
        await self._store.append_event(
            ATTEvent(
                project_id=project_id,
                event_type=event_type,
                payload=payload,
            )
        )
