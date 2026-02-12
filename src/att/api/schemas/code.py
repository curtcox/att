"""Code API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class WriteFileRequest(BaseModel):
    """Write file payload."""

    content: str


class SearchRequest(BaseModel):
    """Search request payload."""

    pattern: str
