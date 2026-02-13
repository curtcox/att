"""MCP API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

from att.mcp.client import ErrorCategory, ServerStatus


class RegisterMCPServerRequest(BaseModel):
    """Create/register MCP server payload."""

    name: str
    url: HttpUrl


class MCPCapabilitySnapshotResponse(BaseModel):
    """Last known capability snapshot for one MCP server."""

    protocol_version: str | None
    server_info: dict[str, Any] | None
    capabilities: dict[str, Any] | None
    captured_at: datetime


class MCPServerResponse(BaseModel):
    """MCP server status payload."""

    name: str
    url: str
    status: ServerStatus
    last_error: str | None
    last_error_category: ErrorCategory | None
    retry_count: int
    last_checked_at: datetime | None
    next_retry_at: datetime | None
    initialized: bool
    protocol_version: str | None
    last_initialized_at: datetime | None
    initialization_expires_at: datetime | None
    capability_snapshot: MCPCapabilitySnapshotResponse | None = None


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


class MCPInvocationAttemptResponse(BaseModel):
    """One server attempt in invocation failure diagnostics."""

    server: str
    stage: Literal["initialize", "invoke"]
    success: bool
    error: str | None = None
    error_category: ErrorCategory | None = None


class MCPInvocationErrorDetailResponse(BaseModel):
    """Deterministic detail payload for invocation failures."""

    message: str
    method: str | None = None
    attempts: list[MCPInvocationAttemptResponse] = Field(default_factory=list)
