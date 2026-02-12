"""Test execution utilities."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RunResult:
    """Test run summary."""

    command: str
    returncode: int
    output: str


class TestRunner:
    """Execute tests in project context."""

    def run(self, project_path: Path, suite: str = "unit") -> RunResult:
        target = {
            "unit": "tests/unit",
            "integration": "tests/integration",
            "e2e": "tests/e2e",
            "property": "tests/property",
            "all": "tests",
        }.get(suite, "tests")
        command = ["pytest", target]
        completed = subprocess.run(
            command,
            cwd=project_path,
            check=False,
            capture_output=True,
            text=True,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return RunResult(
            command=" ".join(command),
            returncode=completed.returncode,
            output=output,
        )
