"""MCP API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl

from att.mcp.client import ServerStatus


class RegisterMCPServerRequest(BaseModel):
    """Create/register MCP server payload."""

    name: str
    url: HttpUrl


class MCPServerResponse(BaseModel):
    """MCP server status payload."""

    name: str
    url: str
    status: ServerStatus
    last_error: str | None
    retry_count: int
    last_checked_at: datetime | None
    next_retry_at: datetime | None


class MCPServersResponse(BaseModel):
    """Collection of MCP servers."""

    items: list[MCPServerResponse]


class MCPToolResponse(BaseModel):
    """MCP tool descriptor response."""

    name: str
    description: str


class MCPResourceResponse(BaseModel):
    """MCP resource descriptor response."""

    uri: str
    description: str
