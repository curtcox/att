from pathlib import Path

import pytest

from att.core.project_manager import CreateProjectInput, ProjectManager
from att.db.store import SQLiteStore


@pytest.mark.asyncio
async def test_project_manager_create_and_list(tmp_path: Path) -> None:
    manager = ProjectManager(SQLiteStore(tmp_path / "att.db"))
    created = await manager.create(CreateProjectInput(name="demo", path=tmp_path / "demo"))

    projects = await manager.list()
    assert len(projects) == 1
    assert projects[0].id == created.id
