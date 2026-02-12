"""Project lifecycle management."""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path

from att.db.store import SQLiteStore
from att.models.events import ATTEvent, EventType
from att.models.project import Project, ProjectStatus


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

    async def clone(self, payload: CreateProjectInput) -> Project:
        if not payload.git_remote:
            msg = "git_remote is required for clone"
            raise ValueError(msg)
        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            payload.git_remote,
            str(payload.path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        output = stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")
        if process.returncode != 0:
            msg = f"git clone failed: {output.strip()}"
            raise RuntimeError(msg)

        project = Project(
            name=payload.name,
            path=payload.path,
            git_remote=payload.git_remote,
            nat_config_path=payload.nat_config_path,
            status=ProjectStatus.CLONED,
        )
        await self._store.upsert_project(project)
        await self._store.append_event(
            ATTEvent(
                project_id=project.id,
                event_type=EventType.PROJECT_CREATED,
                payload={
                    "name": project.name,
                    "source": "clone",
                    "git_remote": project.git_remote or "",
                },
            )
        )
        return project

    async def download(self, project_id: str, archive_basename: Path | None = None) -> Path:
        project = await self._store.get_project(project_id)
        if project is None:
            msg = f"Project not found: {project_id}"
            raise ValueError(msg)
        if not project.path.exists():
            msg = f"Project path does not exist: {project.path}"
            raise ValueError(msg)

        base = (
            archive_basename
            if archive_basename is not None
            else project.path.parent / f"{project.name}-{project.id}"
        )
        base.parent.mkdir(parents=True, exist_ok=True)
        archive = shutil.make_archive(str(base), "zip", root_dir=str(project.path))
        return Path(archive)

    async def list(self) -> list[Project]:
        return await self._store.list_projects()

    async def get(self, project_id: str) -> Project | None:
        return await self._store.get_project(project_id)

    async def delete(self, project_id: str) -> None:
        await self._store.delete_project(project_id)
