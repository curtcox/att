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


class CloneProjectRequest(BaseModel):
    """Payload for cloning a project from git remote."""

    name: str
    path: Path
    git_remote: str
    nat_config_path: Path | None = None


class ProjectsResponse(BaseModel):
    """Collection response for projects."""

    items: list[Project]
