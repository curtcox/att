"""Event API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventResponse(BaseModel):
    """Event record payload."""

    id: str
    event_type: str
    payload: dict[str, Any]
    timestamp: datetime


class EventsResponse(BaseModel):
    """Collection of events."""

    items: list[EventResponse]
