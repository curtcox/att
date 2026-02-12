"""Coordinate multi-step workflows across managers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from att.core.code_manager import CodeManager
from att.core.git_manager import GitManager
from att.core.test_runner import RunResult, TestRunner


@dataclass(slots=True)
class ChangeWorkflowResult:
    """Result from orchestrated change workflow."""

    diff: str
    test_result: RunResult


class ToolOrchestrator:
    """Execute common workflow sequences."""

    def __init__(
        self,
        code_manager: CodeManager,
        git_manager: GitManager,
        test_runner: TestRunner,
    ) -> None:
        self._code = code_manager
        self._git = git_manager
        self._tests = test_runner

    def apply_change_and_test(
        self,
        project_path: Path,
        rel_path: str,
        new_content: str,
    ) -> ChangeWorkflowResult:
        old_content = self._code.read_file(project_path, rel_path)
        self._code.write_file(project_path, rel_path, new_content)
        diff = self._code.diff(
            old_content,
            new_content,
            from_name=f"a/{rel_path}",
            to_name=f"b/{rel_path}",
        )
        test_result = self._tests.run(project_path, suite="unit")
        return ChangeWorkflowResult(diff=diff, test_result=test_result)

    def status(self, project_path: Path) -> str:
        return self._git.status(project_path).output
