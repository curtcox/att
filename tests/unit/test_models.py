from pathlib import Path

from att.models.events import ATTEvent, EventType
from att.models.project import Project, ProjectStatus


def test_project_defaults() -> None:
    project = Project(name="demo", path=Path("/tmp/demo"))
    assert project.status is ProjectStatus.CREATED
    assert project.id


def test_event_defaults() -> None:
    event = ATTEvent(project_id="p1", event_type=EventType.TEST_RUN)
    assert event.id
    assert event.payload == {}
