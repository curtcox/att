"""Async SQLite persistence for ATT models."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite

from att.db.migrations import apply_migrations
from att.models.events import ATTEvent, EventType
from att.models.project import Project, ProjectStatus


class SQLiteStore:
    """Data access layer for projects and events."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(self._db_path)
        conn.row_factory = aiosqlite.Row
        try:
            await apply_migrations(conn)
            yield conn
        finally:
            await conn.close()

    async def upsert_project(self, project: Project) -> None:
        async with self.connection() as conn:
            await conn.execute(
                """
                INSERT INTO projects(
                    id,
                    name,
                    path,
                    git_remote,
                    nat_config_path,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    path=excluded.path,
                    git_remote=excluded.git_remote,
                    nat_config_path=excluded.nat_config_path,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (
                    project.id,
                    project.name,
                    str(project.path),
                    project.git_remote,
                    str(project.nat_config_path) if project.nat_config_path else None,
                    project.status.value,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                ),
            )
            await conn.commit()

    async def list_projects(self) -> list[Project]:
        async with self.connection() as conn:
            cursor = await conn.execute("SELECT * FROM projects ORDER BY created_at ASC")
            rows = await cursor.fetchall()
        return [self._project_from_row(row) for row in rows]

    async def get_project(self, project_id: str) -> Project | None:
        async with self.connection() as conn:
            cursor = await conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return self._project_from_row(row)

    async def delete_project(self, project_id: str) -> None:
        async with self.connection() as conn:
            await conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            await conn.commit()

    async def append_event(self, event: ATTEvent) -> None:
        async with self.connection() as conn:
            await conn.execute(
                """
                INSERT INTO att_events(id, project_id, event_type, payload, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.project_id,
                    event.event_type.value,
                    json.dumps(event.payload),
                    event.timestamp.isoformat(),
                ),
            )
            await conn.commit()

    async def list_events(
        self,
        *,
        project_id: str | None = None,
        event_type: EventType | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ATTEvent]:
        query = "SELECT * FROM att_events WHERE 1 = 1"
        params: list[str] = []

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())

        query += " ORDER BY timestamp ASC"

        async with self.connection() as conn:
            cursor = await conn.execute(query, tuple(params))
            rows = await cursor.fetchall()

        return [self._event_from_row(row) for row in rows]

    @staticmethod
    def _project_from_row(row: aiosqlite.Row) -> Project:
        return Project(
            id=str(row["id"]),
            name=str(row["name"]),
            path=Path(str(row["path"])),
            git_remote=str(row["git_remote"]) if row["git_remote"] else None,
            nat_config_path=Path(str(row["nat_config_path"])) if row["nat_config_path"] else None,
            status=ProjectStatus(str(row["status"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    @staticmethod
    def _event_from_row(row: aiosqlite.Row) -> ATTEvent:
        return ATTEvent(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            event_type=EventType(str(row["event_type"])),
            payload=json.loads(str(row["payload"])),
            timestamp=datetime.fromisoformat(str(row["timestamp"])),
        )
