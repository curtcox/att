"""Event models for ATT audit and observability."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event categories emitted by ATT components."""

    PROJECT_CREATED = "project.created"
    CODE_CHANGED = "code.changed"
    TEST_RUN = "test.run"
    TEST_PASSED = "test.passed"
    TEST_FAILED = "test.failed"
    BUILD_STARTED = "build.started"
    BUILD_COMPLETED = "build.completed"
    DEPLOY_STARTED = "deploy.started"
    DEPLOY_COMPLETED = "deploy.completed"
    GIT_COMMIT = "git.commit"
    GIT_PR_CREATED = "git.pr.created"
    GIT_PR_MERGED = "git.pr.merged"
    ERROR = "error"


class ATTEvent(BaseModel):
    """Append-only event emitted by ATT."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    event_type: EventType
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
