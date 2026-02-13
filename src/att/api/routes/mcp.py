"""MCP routes."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status

from att.api.deps import get_mcp_client_manager
from att.api.schemas.mcp import (
    InvokeToolRequest,
    MCPCapabilitySnapshotResponse,
    MCPConnectionEventResponse,
    MCPConnectionEventsResponse,
    MCPInvocationResponse,
    MCPResourceResponse,
    MCPServerResponse,
    MCPServersResponse,
    MCPToolResponse,
    ReadResourceRequest,
    RegisterMCPServerRequest,
)
from att.mcp.client import (
    ExternalServer,
    JSONValue,
    MCPClientManager,
    MCPInvocationError,
)
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
        initialized=server.initialized,
        protocol_version=server.protocol_version,
        last_initialized_at=server.last_initialized_at,
        capability_snapshot=(
            MCPCapabilitySnapshotResponse(
                protocol_version=server.capability_snapshot.protocol_version,
                server_info=server.capability_snapshot.server_info,
                capabilities=server.capability_snapshot.capabilities,
                captured_at=server.capability_snapshot.captured_at,
            )
            if server.capability_snapshot is not None
            else None
        ),
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


@router.get("/servers/{name}", response_model=MCPServerResponse)
async def get_mcp_server(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = manager.get(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(server)


@router.post("/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def register_mcp_server(
    request: RegisterMCPServerRequest,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = manager.register(request.name, str(request.url))
    return _as_response(server)


@router.delete("/servers/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> None:
    if manager.get(name) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    manager.unregister(name)


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


@router.post("/servers/{name}/initialize", response_model=MCPServerResponse)
async def initialize_mcp_server(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = await manager.initialize_server(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(server)


@router.post("/servers/initialize", response_model=MCPServersResponse)
async def initialize_mcp_servers(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServersResponse:
    return MCPServersResponse(
        items=[_as_response(server) for server in await manager.initialize_all()]
    )


@router.post("/servers/{name}/connect", response_model=MCPServerResponse)
async def connect_mcp_server(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = await manager.connect_server(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(server)


@router.post("/servers/connect", response_model=MCPServersResponse)
async def connect_mcp_servers(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServersResponse:
    return MCPServersResponse(
        items=[_as_response(server) for server in await manager.connect_all()]
    )


@router.get("/events", response_model=MCPConnectionEventsResponse)
async def mcp_connection_events(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPConnectionEventsResponse:
    events = [
        MCPConnectionEventResponse(
            server=event.server,
            from_status=event.from_status,
            to_status=event.to_status,
            reason=event.reason,
            timestamp=event.timestamp,
        )
        for event in manager.list_events()
    ]
    return MCPConnectionEventsResponse(items=events)


@router.post("/invoke/tool", response_model=MCPInvocationResponse)
async def invoke_mcp_tool(
    request: InvokeToolRequest,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPInvocationResponse:
    try:
        arguments = cast(dict[str, JSONValue], request.arguments)
        result = await manager.invoke_tool(
            request.tool_name,
            arguments,
            preferred=request.preferred_servers,
        )
    except MCPInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return MCPInvocationResponse(
        server=result.server,
        method=result.method,
        request_id=result.request_id,
        result=result.result,
        raw_response=result.raw_response,
    )


@router.post("/invoke/resource", response_model=MCPInvocationResponse)
async def invoke_mcp_resource(
    request: ReadResourceRequest,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPInvocationResponse:
    try:
        result = await manager.read_resource(
            request.uri,
            preferred=request.preferred_servers,
        )
    except MCPInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return MCPInvocationResponse(
        server=result.server,
        method=result.method,
        request_id=result.request_id,
        result=result.result,
        raw_response=result.raw_response,
    )
