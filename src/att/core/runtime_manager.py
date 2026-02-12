"""Runtime process manager for nat serve."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RuntimeState:
    """Current runtime status."""

    running: bool
    pid: int | None = None


class RuntimeManager:
    """Manage one nat process at a time."""

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None

    def start(self, project_path: Path, config_path: Path) -> RuntimeState:
        if self._process and self._process.poll() is None:
            return RuntimeState(running=True, pid=self._process.pid)

        self._process = subprocess.Popen(
            ["nat", "serve", "--config", str(config_path)],
            cwd=project_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return RuntimeState(running=True, pid=self._process.pid)

    def stop(self) -> RuntimeState:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._process.wait(timeout=10)
        self._process = None
        return RuntimeState(running=False, pid=None)

    def status(self) -> RuntimeState:
        if self._process and self._process.poll() is None:
            return RuntimeState(running=True, pid=self._process.pid)
        self._process = None
        return RuntimeState(running=False, pid=None)
