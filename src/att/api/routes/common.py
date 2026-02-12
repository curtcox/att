"""Common route helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from att.core.project_manager import ProjectManager
from att.models.project import Project


async def require_project(project_id: str, manager: ProjectManager) -> Project:
    """Load project or return 404."""
    project = await manager.get(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
