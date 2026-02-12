"""Git API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CommitRequest(BaseModel):
    """Commit payload."""

    message: str


class PushRequest(BaseModel):
    """Push payload."""

    remote: str = "origin"
    branch: str = "HEAD"


class BranchRequest(BaseModel):
    """Branch operation payload."""

    name: str
    checkout: bool = True
