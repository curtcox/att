"""MCP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from att.api.deps import get_mcp_client_manager
from att.api.schemas.mcp import (
    MCPResourceResponse,
    MCPServerResponse,
    MCPServersResponse,
    MCPToolResponse,
    RegisterMCPServerRequest,
)
from att.mcp.client import ExternalServer, MCPClientManager
from att.mcp.server import registered_resources, registered_tools

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


def _as_response(server: ExternalServer) -> MCPServerResponse:
    return MCPServerResponse(
        name=server.name,
        url=server.url,
        status=server.status,
        last_error=server.last_error,
        retry_count=server.retry_count,
        last_checked_at=server.last_checked_at,
        next_retry_at=server.next_retry_at,
    )


@router.get("/tools", response_model=list[MCPToolResponse])
async def mcp_tools() -> list[MCPToolResponse]:
    return [
        MCPToolResponse(name=tool.name, description=tool.description) for tool in registered_tools()
    ]


@router.get("/resources", response_model=list[MCPResourceResponse])
async def mcp_resources() -> list[MCPResourceResponse]:
    return [
        MCPResourceResponse(uri=resource.uri, description=resource.description)
        for resource in registered_resources()
    ]


@router.get("/servers", response_model=MCPServersResponse)
async def list_mcp_servers(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServersResponse:
    return MCPServersResponse(items=[_as_response(server) for server in manager.list_servers()])


@router.post("/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def register_mcp_server(
    request: RegisterMCPServerRequest,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = manager.register(request.name, str(request.url))
    return _as_response(server)


@router.post("/servers/{name}/health-check", response_model=MCPServerResponse)
async def check_mcp_server(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = await manager.health_check_server(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(server)


@router.post("/servers/health-check", response_model=MCPServersResponse)
async def check_mcp_servers(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServersResponse:
    return MCPServersResponse(
        items=[_as_response(server) for server in await manager.health_check_all()]
    )
