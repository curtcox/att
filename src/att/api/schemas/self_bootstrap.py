"""Self-bootstrap API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SelfBootstrapRequestModel(BaseModel):
    """Run request for self-bootstrap cycle."""

    file_path: str
    content: str
    commit_message: str
    suite: str = "unit"
    branch_name: str | None = None
    ci_timeout_seconds: int = 600
    ci_initial_poll_seconds: int = 10
    ci_max_poll_seconds: int = 60
    health_check_target: str | None = None


class SelfBootstrapResponseModel(BaseModel):
    """Self-bootstrap cycle execution result."""

    branch_name: str
    committed: bool
    pushed: bool
    ci_status: str
    health_status: str
    success: bool
    test_returncode: int
    event_ids: list[str] = Field(default_factory=list)
