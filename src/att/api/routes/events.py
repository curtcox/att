"""Project event routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from att.api.deps import get_project_manager, get_store
from att.api.routes.common import require_project
from att.api.schemas.events import EventResponse, EventsResponse
from att.core.project_manager import ProjectManager
from att.db.store import SQLiteStore
from att.models.events import EventType

router = APIRouter(prefix="/api/v1/projects/{project_id}/events", tags=["events"])


@router.get("", response_model=EventsResponse)
async def list_project_events(
    project_id: str,
    event_type: str | None = None,
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    manager: ProjectManager = Depends(get_project_manager),
    store: SQLiteStore = Depends(get_store),
) -> EventsResponse:
    await require_project(project_id, manager)

    parsed_event_type: EventType | None = None
    if event_type is not None:
        try:
            parsed_event_type = EventType(event_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid event_type",
            ) from exc

    events = await store.list_events(
        project_id=project_id,
        event_type=parsed_event_type,
        since=since,
        until=until,
    )
    return EventsResponse(
        items=[
            EventResponse(
                id=event.id,
                event_type=event.event_type.value,
                payload=event.payload,
                timestamp=event.timestamp,
            )
            for event in events
        ]
    )
