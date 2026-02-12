"""Project domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Lifecycle status for a managed project."""

    CREATED = "created"
    CLONED = "cloned"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class Project(BaseModel):
    """Managed project metadata."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    path: Path
    git_remote: str | None = None
    nat_config_path: Path | None = None
    status: ProjectStatus = ProjectStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Update mutation timestamp."""
        self.updated_at = datetime.now(UTC)
