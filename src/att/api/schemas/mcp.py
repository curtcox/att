"""MCP API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

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


class MCPConnectionEventResponse(BaseModel):
    """Server connection transition event response."""

    server: str
    from_status: ServerStatus
    to_status: ServerStatus
    reason: str
    timestamp: datetime


class MCPConnectionEventsResponse(BaseModel):
    """Collection of connection transition events."""

    items: list[MCPConnectionEventResponse]


class MCPToolResponse(BaseModel):
    """MCP tool descriptor response."""

    name: str
    description: str


class MCPResourceResponse(BaseModel):
    """MCP resource descriptor response."""

    uri: str
    description: str


class InvokeToolRequest(BaseModel):
    """Tool invocation payload."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    preferred_servers: list[str] | None = None


class ReadResourceRequest(BaseModel):
    """Resource read payload."""

    uri: str
    preferred_servers: list[str] | None = None


class MCPInvocationResponse(BaseModel):
    """MCP invocation response payload."""

    server: str
    method: str
    request_id: str
    result: Any
    raw_response: dict[str, Any]
