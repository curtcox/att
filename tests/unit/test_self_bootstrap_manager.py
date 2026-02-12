from __future__ import annotations

from pathlib import Path

import pytest

from att.core.git_manager import GitResult
from att.core.self_bootstrap_manager import SelfBootstrapManager, SelfBootstrapRequest
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
async def test_self_bootstrap_success_with_ci_and_health(tmp_path: Path) -> None:
    statuses = ["pending", "pending", "success"]
    sleeps: list[float] = []

    async def ci_checker(project_id: str, branch: str) -> str:
        return statuses.pop(0)

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    async def health_checker(target: str) -> bool:
        return True

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
        ci_timeout_seconds=120,
        ci_initial_poll_seconds=1,
        ci_max_poll_seconds=4,
        health_check_target="http://localhost:8000/api/v1/health",
    )

    result = await manager.execute(request)

    assert result.success is True
    assert result.ci_status == "success"
    assert result.health_status == "healthy"
    assert sleeps == [1.0, 2.0]


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
