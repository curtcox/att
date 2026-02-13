from __future__ import annotations

from pathlib import Path

import pytest

from att.core.git_manager import GitResult
from att.core.self_bootstrap_manager import (
    RestartWatchdogSignal,
    SelfBootstrapManager,
    SelfBootstrapRequest,
)
from att.core.test_runner import RunResult
from att.core.tool_orchestrator import WorkflowRunResult
from att.db.store import SQLiteStore
from att.models.events import ATTEvent, EventType


class FakeGitManager:
    def __init__(self) -> None:
        self.branches: list[str] = []
        self.pushes: list[str] = []

    def branch(self, project_path: Path, name: str, *, checkout: bool = True) -> GitResult:
        self.branches.append(name)
        return GitResult(command="git checkout -b", output=name)

    def push(self, project_path: Path, remote: str = "origin", branch: str = "HEAD") -> GitResult:
        self.pushes.append(branch)
        return GitResult(command="git push", output=branch)


class FakeOrchestrator:
    def __init__(self, committed: bool, returncode: int) -> None:
        self.committed = committed
        self.returncode = returncode

    async def run_change_workflow(
        self,
        *,
        project_id: str,
        project_path: Path,
        rel_path: str,
        new_content: str,
        suite: str,
        commit_message: str | None,
    ) -> WorkflowRunResult:
        return WorkflowRunResult(
            diff="diff",
            test_result=RunResult(command="pytest", returncode=self.returncode, output="out"),
            committed=self.committed,
            commit_output="committed" if self.committed else None,
            events=[
                ATTEvent(project_id=project_id, event_type=EventType.CODE_CHANGED, payload={}),
                ATTEvent(project_id=project_id, event_type=EventType.TEST_RUN, payload={}),
                ATTEvent(
                    project_id=project_id,
                    event_type=(
                        EventType.TEST_PASSED if self.returncode == 0 else EventType.TEST_FAILED
                    ),
                    payload={},
                ),
            ],
        )


@pytest.mark.asyncio
async def test_self_bootstrap_success_with_ci_pr_merge_and_health(tmp_path: Path) -> None:
    statuses = ["pending", "pending", "success"]
    sleeps: list[float] = []

    async def ci_checker(project_id: str, branch: str) -> str:
        return statuses.pop(0)

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    async def health_checker(target: str) -> bool:
        return True

    async def pr_creator(project_id: str, branch_name: str) -> str:
        return f"https://example.com/{project_id}/{branch_name}"

    async def pr_merger(project_id: str, pr_url: str) -> bool:
        return True

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        health_checker=health_checker,
        pr_creator=pr_creator,
        pr_merger=pr_merger,
        sleeper=sleeper,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        ci_timeout_seconds=120,
        ci_initial_poll_seconds=1,
        ci_max_poll_seconds=4,
        health_check_target="http://localhost:8000/api/v1/health",
    )

    result = await manager.execute(request)

    assert result.success is True
    assert result.ci_status == "success"
    assert result.pr_url == "https://example.com/p1/codex/test-branch"
    assert result.merged is True
    assert result.restart_watchdog_status == "not_run"
    assert result.health_status == "healthy"
    assert result.rollback_performed is False
    assert sleeps == [1.0, 2.0]


@pytest.mark.asyncio
async def test_self_bootstrap_rolls_back_when_health_check_fails(tmp_path: Path) -> None:
    async def ci_checker(project_id: str, branch: str) -> str:
        return "success"

    async def pr_creator(project_id: str, branch_name: str) -> str:
        return "https://example.com/pr/1"

    async def pr_merger(project_id: str, pr_url: str) -> bool:
        return True

    async def deployer(project_id: str, target: str) -> bool:
        return True

    async def health_checker(target: str) -> bool:
        return False

    async def rollback_executor(project_id: str, target: str) -> bool:
        return True

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        health_checker=health_checker,
        pr_creator=pr_creator,
        pr_merger=pr_merger,
        deployer=deployer,
        rollback_executor=rollback_executor,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        deploy_target="att-service",
        health_check_target="http://localhost:8000/api/v1/health",
    )

    result = await manager.execute(request)

    assert result.success is False
    assert result.restart_watchdog_status == "not_run"
    assert result.health_status == "unhealthy"
    assert result.rollback_performed is True
    assert result.rollback_succeeded is True


@pytest.mark.asyncio
async def test_self_bootstrap_health_retries_before_failing(tmp_path: Path) -> None:
    health_states = [False, True]
    sleeps: list[float] = []

    async def ci_checker(project_id: str, branch: str) -> str:
        return "success"

    async def health_checker(target: str) -> bool:
        return health_states.pop(0)

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        health_checker=health_checker,
        sleeper=sleeper,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        health_check_target="http://localhost:8000/api/v1/health",
        health_check_retries=2,
        health_check_interval_seconds=3,
    )

    result = await manager.execute(request)

    assert result.success is True
    assert result.restart_watchdog_status == "not_run"
    assert result.health_status == "healthy"
    assert sleeps == [3.0]


@pytest.mark.asyncio
async def test_self_bootstrap_returns_failure_when_tests_fail(tmp_path: Path) -> None:
    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=False, returncode=1),
        store=SQLiteStore(tmp_path / "att.db"),
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
    )

    result = await manager.execute(request)

    assert result.success is False
    assert result.committed is False
    assert result.pushed is False
    assert result.restart_watchdog_status == "not_run"


@pytest.mark.asyncio
async def test_self_bootstrap_returns_failure_on_ci_timeout(tmp_path: Path) -> None:
    async def ci_checker(project_id: str, branch: str) -> str:
        return "pending"

    async def sleeper(seconds: float) -> None:
        return None

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        sleeper=sleeper,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        ci_timeout_seconds=0,
        ci_initial_poll_seconds=1,
        ci_max_poll_seconds=2,
    )

    result = await manager.execute(request)

    assert result.success is False
    assert result.ci_status == "timeout"
    assert result.restart_watchdog_status == "not_run"


@pytest.mark.asyncio
async def test_self_bootstrap_restart_watchdog_retries_and_succeeds(tmp_path: Path) -> None:
    watchdog_states = [False, True]
    sleeps: list[float] = []

    async def ci_checker(project_id: str, branch: str) -> str:
        return "success"

    async def deployer(project_id: str, target: str) -> bool:
        return True

    async def restart_watchdog(project_id: str, target: str) -> bool:
        return watchdog_states.pop(0)

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        deployer=deployer,
        restart_watchdog=restart_watchdog,
        sleeper=sleeper,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        deploy_target="att-service",
        restart_watchdog_retries=2,
        restart_watchdog_interval_seconds=4,
    )

    result = await manager.execute(request)

    assert result.success is True
    assert result.restart_watchdog_status == "stable"
    assert result.restart_watchdog_reason == "runtime_healthy"
    assert result.rollback_performed is False
    assert sleeps == [4.0]


@pytest.mark.asyncio
async def test_self_bootstrap_restart_watchdog_failure_triggers_rollback(tmp_path: Path) -> None:
    async def ci_checker(project_id: str, branch: str) -> str:
        return "success"

    async def deployer(project_id: str, target: str) -> bool:
        return True

    async def restart_watchdog(project_id: str, target: str) -> bool:
        return False

    async def rollback_executor(project_id: str, target: str) -> bool:
        return True

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        deployer=deployer,
        restart_watchdog=restart_watchdog,
        rollback_executor=rollback_executor,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        deploy_target="att-service",
        restart_watchdog_retries=1,
    )

    result = await manager.execute(request)

    assert result.success is False
    assert result.restart_watchdog_status == "unstable"
    assert result.restart_watchdog_reason == "runtime_unhealthy"
    assert result.health_status == "not_run"
    assert result.rollback_performed is True
    assert result.rollback_succeeded is True


@pytest.mark.asyncio
async def test_self_bootstrap_restart_watchdog_signal_reason_propagates(tmp_path: Path) -> None:
    async def ci_checker(project_id: str, branch: str) -> str:
        return "success"

    async def deployer(project_id: str, target: str) -> bool:
        return True

    async def restart_watchdog(project_id: str, target: str) -> RestartWatchdogSignal:
        return RestartWatchdogSignal(
            stable=False,
            reason="process_not_running",
            probe="process",
        )

    async def rollback_executor(project_id: str, target: str) -> bool:
        return True

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        deployer=deployer,
        restart_watchdog=restart_watchdog,
        rollback_executor=rollback_executor,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        deploy_target="att-service",
        restart_watchdog_retries=1,
    )

    result = await manager.execute(request)

    assert result.success is False
    assert result.restart_watchdog_status == "unstable"
    assert result.restart_watchdog_reason == "process_not_running"
    assert result.rollback_performed is True


@pytest.mark.asyncio
async def test_self_bootstrap_health_failure_uses_previous_release_for_rollback(tmp_path: Path) -> None:
    rollback_targets: list[str | None] = []

    async def ci_checker(project_id: str, branch: str) -> str:
        return "success"

    async def deployer(project_id: str, target: str) -> bool:
        return True

    async def health_checker(target: str) -> bool:
        return False

    async def rollback_executor(project_id: str, target: str, release_id: str | None) -> bool:
        rollback_targets.append(release_id)
        return True

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        deployer=deployer,
        health_checker=health_checker,
        rollback_executor=rollback_executor,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        deploy_target="att-service",
        requested_release_id="release-2",
        previous_release_id="release-1",
        health_check_target="http://localhost:8000/api/v1/health",
    )

    result = await manager.execute(request)

    assert result.success is False
    assert result.deployed_release_id == "release-2"
    assert result.rollback_target_release_id == "release-1"
    assert rollback_targets == ["release-1"]


@pytest.mark.asyncio
async def test_self_bootstrap_explicit_rollback_release_overrides_previous(tmp_path: Path) -> None:
    rollback_targets: list[str | None] = []

    async def ci_checker(project_id: str, branch: str) -> str:
        return "success"

    async def deployer(project_id: str, target: str) -> bool:
        return True

    async def restart_watchdog(project_id: str, target: str) -> bool:
        return False

    async def rollback_executor(project_id: str, target: str, release_id: str | None) -> bool:
        rollback_targets.append(release_id)
        return True

    manager = SelfBootstrapManager(
        git_manager=FakeGitManager(),
        orchestrator=FakeOrchestrator(committed=True, returncode=0),
        store=SQLiteStore(tmp_path / "att.db"),
        ci_checker=ci_checker,
        deployer=deployer,
        restart_watchdog=restart_watchdog,
        rollback_executor=rollback_executor,
    )

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    request = SelfBootstrapRequest(
        project_id="p1",
        project_path=project_path,
        file_path="app.py",
        content="x",
        commit_message="feat: auto",
        branch_name="codex/test-branch",
        deploy_target="att-service",
        requested_release_id="release-9",
        previous_release_id="release-8",
        rollback_release_id="release-7",
        restart_watchdog_retries=1,
    )

    result = await manager.execute(request)

    assert result.success is False
    assert result.deployed_release_id == "release-9"
    assert result.rollback_target_release_id == "release-7"
    assert rollback_targets == ["release-7"]
