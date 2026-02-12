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

    def actions(self, project_path: Path, limit: int = 10) -> GitResult:
        """Get GitHub Actions runs using gh CLI."""
        return self._run_command(
            project_path,
            "gh",
            "run",
            "list",
            "--limit",
            str(limit),
            "--json",
            "databaseId,status,conclusion,displayTitle,headBranch",
        )

    def pr_create(
        self,
        project_path: Path,
        *,
        title: str,
        body: str,
        base: str = "dev",
        head: str | None = None,
    ) -> GitResult:
        """Create pull request using gh CLI."""
        args = [
            "gh",
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
        ]
        if head:
            args.extend(["--head", head])
        return self._run_command(project_path, *args)

    def pr_merge(
        self,
        project_path: Path,
        *,
        pull_request: str,
        strategy: str = "squash",
    ) -> GitResult:
        """Merge pull request using gh CLI."""
        mode = {
            "squash": "--squash",
            "merge": "--merge",
            "rebase": "--rebase",
        }.get(strategy, "--squash")
        return self._run_command(
            project_path, "gh", "pr", "merge", pull_request, mode, "--delete-branch"
        )

    def pr_reviews(self, project_path: Path, *, pull_request: str) -> GitResult:
        """Get pull request reviews using gh CLI."""
        return self._run_command(
            project_path,
            "gh",
            "pr",
            "view",
            pull_request,
            "--json",
            "reviews",
        )

    @staticmethod
    def _run_git(project_path: Path, *args: str) -> GitResult:
        command = ["git", *args]
        return GitManager._run_command(project_path, *command)

    @staticmethod
    def _run_command(project_path: Path, *command: str) -> GitResult:
        completed = subprocess.run(
            [*command],
            cwd=project_path,
            check=False,
            capture_output=True,
            text=True,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        if completed.returncode != 0:
            msg = f"{' '.join(command)} failed: {output.strip()}"
            raise RuntimeError(msg)
        return GitResult(command=" ".join(command), output=output.strip())
