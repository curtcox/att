"""Project lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from att.db.store import SQLiteStore
from att.models.events import ATTEvent, EventType
from att.models.project import Project


@dataclass(slots=True)
class CreateProjectInput:
    """Input payload for project creation."""

    name: str
    path: Path
    git_remote: str | None = None
    nat_config_path: Path | None = None


class ProjectManager:
    """Manage registered projects."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    async def create(self, payload: CreateProjectInput) -> Project:
        project = Project(
            name=payload.name,
            path=payload.path,
            git_remote=payload.git_remote,
            nat_config_path=payload.nat_config_path,
        )
        await self._store.upsert_project(project)
        await self._store.append_event(
            ATTEvent(
                project_id=project.id,
                event_type=EventType.PROJECT_CREATED,
                payload={"name": project.name},
            )
        )
        return project

    async def list(self) -> list[Project]:
        return await self._store.list_projects()

    async def get(self, project_id: str) -> Project | None:
        return await self._store.get_project(project_id)

    async def delete(self, project_id: str) -> None:
        await self._store.delete_project(project_id)
