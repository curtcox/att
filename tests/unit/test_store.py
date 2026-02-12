from pathlib import Path

import pytest

from att.db.store import SQLiteStore
from att.models.events import ATTEvent, EventType
from att.models.project import Project


@pytest.mark.asyncio
async def test_store_project_crud(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "att.db")
    project = Project(name="demo", path=tmp_path / "demo")

    await store.upsert_project(project)

    fetched = await store.get_project(project.id)
    assert fetched is not None
    assert fetched.name == "demo"

    listed = await store.list_projects()
    assert len(listed) == 1

    await store.delete_project(project.id)
    assert await store.get_project(project.id) is None


@pytest.mark.asyncio
async def test_store_event_filters(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "att.db")
    project = Project(name="demo", path=tmp_path / "demo")
    await store.upsert_project(project)

    event = ATTEvent(
        project_id=project.id,
        event_type=EventType.TEST_RUN,
        payload={"suite": "unit"},
    )
    await store.append_event(event)

    events = await store.list_events(project_id=project.id, event_type=EventType.TEST_RUN)
    assert len(events) == 1
    assert events[0].payload["suite"] == "unit"
