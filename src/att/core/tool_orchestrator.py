"""Coordinate multi-step workflows across managers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from att.core.code_manager import CodeManager
from att.core.git_manager import GitManager
from att.core.test_runner import RunResult, TestRunner
from att.db.store import SQLiteStore
from att.models.events import ATTEvent, EventType


@dataclass(slots=True)
class WorkflowRunResult:
    """Result from an orchestrated change workflow."""

    diff: str
    test_result: RunResult
    committed: bool
    commit_output: str | None
    events: list[ATTEvent]


class ToolOrchestrator:
    """Execute common workflow sequences across managers."""

    def __init__(
        self,
        code_manager: CodeManager,
        git_manager: GitManager,
        test_runner: TestRunner,
        store: SQLiteStore | None = None,
    ) -> None:
        self._code = code_manager
        self._git = git_manager
        self._tests = test_runner
        self._store = store

    async def run_change_workflow(
        self,
        *,
        project_id: str,
        project_path: Path,
        rel_path: str,
        new_content: str,
        suite: str = "unit",
        commit_message: str | None = None,
    ) -> WorkflowRunResult:
        """Apply code change, run tests, and optionally commit on green tests."""
        old_content = self._code.read_file(project_path, rel_path)
        self._code.write_file(project_path, rel_path, new_content)
        diff = self._code.diff(
            old_content,
            new_content,
            from_name=f"a/{rel_path}",
            to_name=f"b/{rel_path}",
        )

        events: list[ATTEvent] = []
        code_event = ATTEvent(
            project_id=project_id,
            event_type=EventType.CODE_CHANGED,
            payload={"path": rel_path, "diff_chars": len(diff)},
        )
        await self._record_event(code_event, events)

        test_run_event = ATTEvent(
            project_id=project_id,
            event_type=EventType.TEST_RUN,
            payload={"suite": suite},
        )
        await self._record_event(test_run_event, events)

        test_result = self._tests.run(project_path, suite=suite)
        pass_fail_event = ATTEvent(
            project_id=project_id,
            event_type=(
                EventType.TEST_PASSED if test_result.returncode == 0 else EventType.TEST_FAILED
            ),
            payload={
                "suite": suite,
                "returncode": test_result.returncode,
            },
        )
        await self._record_event(pass_fail_event, events)

        committed = False
        commit_output: str | None = None
        if commit_message and test_result.returncode == 0:
            commit_result = self._git.commit(project_path, commit_message)
            committed = True
            commit_output = commit_result.output
            git_event = ATTEvent(
                project_id=project_id,
                event_type=EventType.GIT_COMMIT,
                payload={"message": commit_message},
            )
            await self._record_event(git_event, events)

        return WorkflowRunResult(
            diff=diff,
            test_result=test_result,
            committed=committed,
            commit_output=commit_output,
            events=events,
        )

    def status(self, project_path: Path) -> str:
        """Return current git working tree status."""
        return self._git.status(project_path).output

    async def _record_event(self, event: ATTEvent, sink: list[ATTEvent]) -> None:
        sink.append(event)
        if self._store is not None:
            await self._store.append_event(event)
