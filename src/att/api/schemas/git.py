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


class PRCreateRequest(BaseModel):
    """Pull request creation payload."""

    title: str
    body: str
    base: str = "dev"
    head: str | None = None


class PRMergeRequest(BaseModel):
    """Pull request merge payload."""

    pull_request: str
    strategy: str = "squash"


class PRReviewsRequest(BaseModel):
    """Pull request review query payload."""

    pull_request: str
