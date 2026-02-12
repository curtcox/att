"""Deployment management primitives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from att.core.runtime_manager import RuntimeManager, RuntimeState


@dataclass(slots=True)
class DeployStatus:
    """Deployment status summary."""

    built: bool
    running: bool
    message: str


class DeployManager:
    """Perform local build and runtime deployment."""

    def __init__(self, runtime_manager: RuntimeManager) -> None:
        self._runtime_manager = runtime_manager

    def build(self, project_path: Path) -> DeployStatus:
        pyproject = project_path / "pyproject.toml"
        if not pyproject.exists():
            return DeployStatus(built=False, running=False, message="pyproject.toml not found")
        return DeployStatus(built=True, running=False, message="build checks passed")

    def run(self, project_path: Path, config_path: Path) -> DeployStatus:
        state: RuntimeState = self._runtime_manager.start(project_path, config_path)
        return DeployStatus(built=True, running=state.running, message="runtime started")

    def status(self) -> DeployStatus:
        state = self._runtime_manager.status()
        return DeployStatus(built=True, running=state.running, message="runtime status")
