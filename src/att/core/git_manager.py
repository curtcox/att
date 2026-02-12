"""Git operations for managed projects."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GitResult:
    """Result from running a git command."""

    command: str
    output: str


class GitManager:
    """Thin wrapper around git CLI."""

    def status(self, project_path: Path) -> GitResult:
        return self._run_git(project_path, "status", "--short")

    def commit(self, project_path: Path, message: str) -> GitResult:
        self._run_git(project_path, "add", ".")
        return self._run_git(project_path, "commit", "-m", message)

    def push(self, project_path: Path, remote: str = "origin", branch: str = "HEAD") -> GitResult:
        return self._run_git(project_path, "push", remote, branch)

    def branch(self, project_path: Path, name: str, *, checkout: bool = True) -> GitResult:
        if checkout:
            return self._run_git(project_path, "checkout", "-b", name)
        return self._run_git(project_path, "branch", name)

    def log(self, project_path: Path, limit: int = 20) -> GitResult:
        return self._run_git(project_path, "log", f"--max-count={limit}", "--oneline")

    @staticmethod
    def _run_git(project_path: Path, *args: str) -> GitResult:
        command = ["git", *args]
        completed = subprocess.run(
            command,
            cwd=project_path,
            check=False,
            capture_output=True,
            text=True,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        if completed.returncode != 0:
            msg = f"git {' '.join(args)} failed: {output.strip()}"
            raise RuntimeError(msg)
        return GitResult(command=" ".join(command), output=output.strip())
