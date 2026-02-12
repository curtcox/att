"""Project API schemas."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from att.models.project import Project


class CreateProjectRequest(BaseModel):
    """Payload for creating a project."""

    name: str
    path: Path
    git_remote: str | None = None
    nat_config_path: Path | None = None


class ProjectsResponse(BaseModel):
    """Collection response for projects."""

    items: list[Project]
