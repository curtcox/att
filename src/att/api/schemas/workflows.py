"""Workflow API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class RunChangeWorkflowRequest(BaseModel):
    """Request payload for change-test workflow."""

    file_path: str
    content: str
    suite: str = "unit"
    commit_message: str | None = None


class RunChangeWorkflowResponse(BaseModel):
    """Workflow execution result payload."""

    diff: str
    test_command: str
    test_returncode: int
    test_output: str
    committed: bool
    commit_output: str | None
    event_ids: list[str]
