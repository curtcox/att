"""Self-bootstrap workflow manager."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from att.core.git_manager import GitManager
from att.core.tool_orchestrator import ToolOrchestrator, WorkflowRunResult
from att.db.store import SQLiteStore
from att.models.events import ATTEvent, EventType

type CIStatus = Literal["pending", "success", "failure"]
type CIChecker = Callable[[str, str], Awaitable[CIStatus]]
type HealthChecker = Callable[[str], Awaitable[bool]]
type Sleeper = Callable[[float], Awaitable[None]]


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
    health_check_target: str | None = None


@dataclass(slots=True)
class SelfBootstrapResult:
    """Output summary for a self-bootstrap cycle."""

    branch_name: str
    committed: bool
    pushed: bool
    ci_status: str
    health_status: str
    success: bool
    workflow_result: WorkflowRunResult


class SelfBootstrapManager:
    """Coordinate branch, change, test, CI, and health checks."""

    def __init__(
        self,
        *,
        git_manager: GitManager,
        orchestrator: ToolOrchestrator,
        store: SQLiteStore,
        ci_checker: CIChecker | None = None,
        health_checker: HealthChecker | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._git = git_manager
        self._orchestrator = orchestrator
        self._store = store
        self._ci_checker = ci_checker
        self._health_checker = health_checker
        self._sleep = sleeper or asyncio.sleep

    async def execute(self, request: SelfBootstrapRequest) -> SelfBootstrapResult:
        """Run a baseline self-bootstrap cycle."""
        branch_name = request.branch_name or f"codex/self-bootstrap-{uuid4().hex[:8]}"

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
                health_status="not_run",
                success=False,
                workflow_result=workflow,
            )

        self._git.push(request.project_path, "origin", branch_name)

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
                    health_status="not_run",
                    success=False,
                    workflow_result=workflow,
                )

        health_status = "not_run"
        if self._health_checker is not None and request.health_check_target is not None:
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.DEPLOY_STARTED,
                payload={"target": request.health_check_target},
            )
            healthy = await self._health_checker(request.health_check_target)
            health_status = "healthy" if healthy else "unhealthy"
            await self._record_event(
                project_id=request.project_id,
                event_type=EventType.DEPLOY_COMPLETED,
                payload={"target": request.health_check_target, "healthy": healthy},
            )
            if not healthy:
                return SelfBootstrapResult(
                    branch_name=branch_name,
                    committed=True,
                    pushed=True,
                    ci_status=ci_status,
                    health_status=health_status,
                    success=False,
                    workflow_result=workflow,
                )

        return SelfBootstrapResult(
            branch_name=branch_name,
            committed=True,
            pushed=True,
            ci_status=ci_status,
            health_status=health_status,
            success=True,
            workflow_result=workflow,
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
