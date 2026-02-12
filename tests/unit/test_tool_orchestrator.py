from __future__ import annotations

from pathlib import Path

import pytest

from att.core.code_manager import CodeManager
from att.core.git_manager import GitResult
from att.core.test_runner import RunResult
from att.core.tool_orchestrator import ToolOrchestrator
from att.db.store import SQLiteStore
from att.models.events import EventType


class FakeGitManager:
    def __init__(self) -> None:
        self.commit_messages: list[str] = []

    def commit(self, project_path: Path, message: str) -> GitResult:
        self.commit_messages.append(message)
        return GitResult(command="git commit", output=f"committed:{message}")

    def status(self, project_path: Path) -> GitResult:
        return GitResult(command="git status --short", output="M file")


class FakeTestRunner:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode

    def run(self, project_path: Path, suite: str = "unit") -> RunResult:
        return RunResult(
            command=f"pytest tests/{suite}",
            returncode=self.returncode,
            output=f"suite={suite}",
        )


@pytest.mark.asyncio
async def test_workflow_records_pass_events_and_optional_commit(tmp_path: Path) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    file_path = project_path / "app.py"
    file_path.write_text("print('old')\n", encoding="utf-8")

    store = SQLiteStore(tmp_path / "att.db")
    git = FakeGitManager()
    tests = FakeTestRunner(returncode=0)
    orchestrator = ToolOrchestrator(CodeManager(), git, tests, store)

    result = await orchestrator.run_change_workflow(
        project_id="p1",
        project_path=project_path,
        rel_path="app.py",
        new_content="print('new')\n",
        suite="unit",
        commit_message="feat: update app",
    )

    assert result.committed is True
    assert result.commit_output == "committed:feat: update app"
    assert "new" in result.diff
    assert git.commit_messages == ["feat: update app"]

    events = await store.list_events(project_id="p1")
    assert [event.event_type for event in events] == [
        EventType.CODE_CHANGED,
        EventType.TEST_RUN,
        EventType.TEST_PASSED,
        EventType.GIT_COMMIT,
    ]


@pytest.mark.asyncio
async def test_workflow_skips_commit_when_tests_fail(tmp_path: Path) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    file_path = project_path / "app.py"
    file_path.write_text("print('old')\n", encoding="utf-8")

    store = SQLiteStore(tmp_path / "att.db")
    git = FakeGitManager()
    tests = FakeTestRunner(returncode=1)
    orchestrator = ToolOrchestrator(CodeManager(), git, tests, store)

    result = await orchestrator.run_change_workflow(
        project_id="p1",
        project_path=project_path,
        rel_path="app.py",
        new_content="print('new')\n",
        suite="unit",
        commit_message="feat: should not commit",
    )

    assert result.committed is False
    assert result.commit_output is None
    assert git.commit_messages == []

    events = await store.list_events(project_id="p1")
    assert [event.event_type for event in events] == [
        EventType.CODE_CHANGED,
        EventType.TEST_RUN,
        EventType.TEST_FAILED,
    ]
