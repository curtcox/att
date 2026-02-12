"""Test API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class RunTestRequest(BaseModel):
    """Test run payload."""

    suite: str = "unit"
    markers: str | None = None
    timeout_seconds: int | None = None
