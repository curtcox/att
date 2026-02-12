"""SQLite migrations for ATT storage."""

from __future__ import annotations

import aiosqlite

SCHEMA_VERSION = 1


async def apply_migrations(conn: aiosqlite.Connection) -> None:
    """Create core schema if missing and set schema version."""
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            git_remote TEXT,
            nat_config_path TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS att_events (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
        """
    )

    await conn.execute("DELETE FROM schema_migrations")
    await conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (SCHEMA_VERSION,))
    await conn.commit()
