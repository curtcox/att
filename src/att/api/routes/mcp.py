"""MCP routes."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, status

from att.api.deps import get_mcp_client_manager
from att.api.schemas.mcp import (
    InvokeToolRequest,
    MCPAdapterSessionResponse,
    MCPAdapterSessionsResponse,
    MCPAdapterSessionStatusResponse,
    MCPCapabilitySnapshotResponse,
    MCPConnectionEventResponse,
    MCPConnectionEventsResponse,
    MCPInvocationAttemptResponse,
    MCPInvocationErrorDetailResponse,
    MCPInvocationEventResponse,
    MCPInvocationEventsResponse,
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
    MCPInvocationAttempt,
    MCPInvocationError,
)
from att.mcp.server import registered_resources, registered_tools

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


def _as_response(server: ExternalServer, manager: MCPClientManager) -> MCPServerResponse:
    adapter_session = manager.adapter_session_diagnostics(server.name)
    adapter_controls_available = manager.supports_adapter_session_controls()
    return MCPServerResponse(
        name=server.name,
        url=server.url,
        status=server.status,
        last_error=server.last_error,
        last_error_category=server.last_error_category,
        retry_count=server.retry_count,
        last_checked_at=server.last_checked_at,
        next_retry_at=server.next_retry_at,
        initialized=server.initialized,
        protocol_version=server.protocol_version,
        last_initialized_at=server.last_initialized_at,
        initialization_expires_at=server.initialization_expires_at,
        adapter_controls_available=adapter_controls_available,
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
        adapter_session=(
            MCPAdapterSessionResponse(
                active=adapter_session.active,
                initialized=adapter_session.initialized,
                last_activity_at=adapter_session.last_activity_at,
            )
            if adapter_session is not None
            else None
        ),
    )


def _invocation_error_detail(exc: MCPInvocationError) -> MCPInvocationErrorDetailResponse:
    def _attempt_response(attempt: MCPInvocationAttempt) -> MCPInvocationAttemptResponse:
        return MCPInvocationAttemptResponse(
            server=attempt.server,
            stage=attempt.stage,
            success=attempt.success,
            error=attempt.error,
            error_category=attempt.error_category,
        )

    return MCPInvocationErrorDetailResponse(
        message=str(exc),
        method=exc.method,
        attempts=[_attempt_response(attempt) for attempt in exc.attempts],
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
    return MCPServersResponse(
        items=[_as_response(server, manager) for server in manager.list_servers()],
        adapter_controls_available=manager.supports_adapter_session_controls(),
    )


@router.get("/servers/{name}", response_model=MCPServerResponse)
async def get_mcp_server(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = manager.get(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(server, manager)


@router.post("/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def register_mcp_server(
    request: RegisterMCPServerRequest,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = manager.register(request.name, str(request.url))
    return _as_response(server, manager)


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
    return _as_response(server, manager)


@router.post("/servers/health-check", response_model=MCPServersResponse)
async def check_mcp_servers(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServersResponse:
    return MCPServersResponse(
        items=[_as_response(server, manager) for server in await manager.health_check_all()],
        adapter_controls_available=manager.supports_adapter_session_controls(),
    )


@router.post("/servers/{name}/initialize", response_model=MCPServerResponse)
async def initialize_mcp_server(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = await manager.initialize_server(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(server, manager)


@router.post("/servers/initialize", response_model=MCPServersResponse)
async def initialize_mcp_servers(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServersResponse:
    return MCPServersResponse(
        items=[_as_response(server, manager) for server in await manager.initialize_all()],
        adapter_controls_available=manager.supports_adapter_session_controls(),
    )


@router.post("/servers/{name}/connect", response_model=MCPServerResponse)
async def connect_mcp_server(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = await manager.connect_server(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(server, manager)


@router.post("/servers/connect", response_model=MCPServersResponse)
async def connect_mcp_servers(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServersResponse:
    return MCPServersResponse(
        items=[_as_response(server, manager) for server in await manager.connect_all()],
        adapter_controls_available=manager.supports_adapter_session_controls(),
    )


@router.get("/adapter-sessions", response_model=MCPAdapterSessionsResponse)
async def mcp_adapter_sessions(
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPAdapterSessionsResponse:
    return MCPAdapterSessionsResponse(
        adapter_controls_available=manager.supports_adapter_session_controls(),
        items=[
            MCPAdapterSessionStatusResponse(
                server=item.server,
                active=item.active,
                initialized=item.initialized,
                last_activity_at=item.last_activity_at,
            )
            for item in manager.list_adapter_sessions()
        ],
    )


@router.post("/servers/{name}/adapter/invalidate", response_model=MCPServerResponse)
async def invalidate_mcp_server_adapter_session(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    server = manager.get(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    if not manager.supports_adapter_session_controls():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Adapter session controls are not available",
        )
    await manager.invalidate_adapter_session(name)
    refreshed = manager.get(name)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(refreshed, manager)


@router.post("/servers/{name}/adapter/refresh", response_model=MCPServerResponse)
async def refresh_mcp_server_adapter_session(
    name: str,
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPServerResponse:
    if manager.get(name) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    if not manager.supports_adapter_session_controls():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Adapter session controls are not available",
        )
    server = await manager.refresh_adapter_session(name)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _as_response(server, manager)


@router.get("/events", response_model=MCPConnectionEventsResponse)
async def mcp_connection_events(
    server: str | None = None,
    correlation_id: str | None = None,
    limit: int | None = Query(default=None, ge=1),
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPConnectionEventsResponse:
    events = [
        MCPConnectionEventResponse(
            server=event.server,
            from_status=event.from_status,
            to_status=event.to_status,
            reason=event.reason,
            timestamp=event.timestamp,
            correlation_id=event.correlation_id,
        )
        for event in manager.list_events(
            server=server,
            correlation_id=correlation_id,
            limit=limit,
        )
    ]
    return MCPConnectionEventsResponse(items=events)


@router.get("/invocation-events", response_model=MCPInvocationEventsResponse)
async def mcp_invocation_events(
    server: str | None = None,
    method: str | None = None,
    request_id: str | None = None,
    limit: int | None = Query(default=None, ge=1),
    manager: MCPClientManager = Depends(get_mcp_client_manager),
) -> MCPInvocationEventsResponse:
    events = [
        MCPInvocationEventResponse(
            server=event.server,
            method=event.method,
            request_id=event.request_id,
            phase=event.phase,
            timestamp=event.timestamp,
            error=event.error,
            error_category=event.error_category,
        )
        for event in manager.list_invocation_events(
            server=server,
            method=method,
            request_id=request_id,
            limit=limit,
        )
    ]
    return MCPInvocationEventsResponse(items=events)


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
            detail=_invocation_error_detail(exc).model_dump(mode="json"),
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
            detail=_invocation_error_detail(exc).model_dump(mode="json"),
        ) from exc
    return MCPInvocationResponse(
        server=result.server,
        method=result.method,
        request_id=result.request_id,
        result=result.result,
        raw_response=result.raw_response,
    )
