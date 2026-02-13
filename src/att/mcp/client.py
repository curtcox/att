"""ATT MCP client management with health/backoff handling."""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Literal, Protocol, cast
from uuid import uuid4

import httpx

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]
type ErrorCategory = Literal[
    "health_check",
    "initialize_error",
    "network_timeout",
    "http_status",
    "invalid_payload",
    "rpc_error",
    "transport_error",
    "unknown",
]
type InvocationPhase = Literal[
    "initialize_start",
    "initialize_success",
    "initialize_failure",
    "invoke_start",
    "invoke_success",
    "invoke_failure",
]


class ServerStatus(StrEnum):
    """Availability state for an external MCP server."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"


@dataclass(slots=True)
class CapabilitySnapshot:
    """Last known MCP capability surface captured at initialize time."""

    protocol_version: str | None
    server_info: JSONObject | None
    capabilities: JSONObject | None
    captured_at: datetime


@dataclass(slots=True)
class ExternalServer:
    """Connected external MCP server and health metadata."""

    name: str
    url: str
    status: ServerStatus = ServerStatus.HEALTHY
    last_error: str | None = None
    last_error_category: ErrorCategory | None = None
    retry_count: int = 0
    last_checked_at: datetime | None = None
    next_retry_at: datetime | None = None
    initialized: bool = False
    protocol_version: str | None = None
    last_initialized_at: datetime | None = None
    initialization_expires_at: datetime | None = None
    capability_snapshot: CapabilitySnapshot | None = None

    @property
    def healthy(self) -> bool:
        """Backwards-compatible health bool view."""
        return self.status is ServerStatus.HEALTHY


@dataclass(slots=True)
class ConnectionEvent:
    """Connection status transition event."""

    server: str
    from_status: ServerStatus
    to_status: ServerStatus
    reason: str
    timestamp: datetime
    correlation_id: str | None = None


@dataclass(slots=True)
class MCPInvocationResult:
    """Normalized result for a single MCP invocation."""

    server: str
    method: str
    request_id: str
    result: JSONValue
    raw_response: JSONObject


@dataclass(slots=True)
class MCPInvocationAttempt:
    """One initialize/invoke attempt against one server."""

    server: str
    stage: Literal["initialize", "invoke"]
    success: bool
    error: str | None = None
    error_category: ErrorCategory | None = None


@dataclass(slots=True)
class MCPInvocationEvent:
    """Lifecycle event for one invocation step against one server."""

    server: str
    method: str
    request_id: str
    phase: InvocationPhase
    timestamp: datetime
    error: str | None = None
    error_category: ErrorCategory | None = None


@dataclass(slots=True)
class AdapterSessionDiagnostics:
    """Non-sensitive diagnostics for one adapter-backed server session."""

    active: bool
    initialized: bool
    last_activity_at: datetime | None


@dataclass(slots=True)
class AdapterSessionStatus:
    """Aggregated adapter session status for one registered server."""

    server: str
    active: bool
    initialized: bool
    last_activity_at: datetime | None


class MCPInvocationError(RuntimeError):
    """Raised when invocation fails across all available servers."""

    def __init__(
        self,
        message: str,
        *,
        method: str | None = None,
        attempts: list[MCPInvocationAttempt] | None = None,
    ) -> None:
        super().__init__(message)
        self.method = method
        self.attempts = list(attempts or [])


class MCPTransportError(RuntimeError):
    """Transport failure with explicit category."""

    def __init__(self, message: str, *, category: ErrorCategory) -> None:
        super().__init__(message)
        self.category = category


class HealthProbe(Protocol):
    """Async probe protocol for MCP health checks."""

    async def __call__(self, server: ExternalServer) -> tuple[bool, str | None]:
        """Return (healthy, error_message)."""


class MCPTransport(Protocol):
    """Async transport protocol for MCP JSON-RPC requests."""

    async def __call__(self, server: ExternalServer, request: JSONObject) -> JSONObject:
        """Send request to one server and return JSON object response."""


class NATMCPSession(Protocol):
    """Minimal MCP SDK session surface used by NAT adapter transport."""

    async def initialize(self) -> Any:
        """Run MCP initialize handshake."""

    async def send_notification(
        self,
        notification: Any,
        related_request_id: str | int | None = None,
    ) -> None:
        """Send one MCP notification."""

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
        progress_callback: Any | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> Any:
        """Call one tool via MCP SDK."""

    async def read_resource(self, uri: Any) -> Any:
        """Read one resource via MCP SDK."""


class NATMCPSessionFactory(Protocol):
    """Factory for endpoint-bound NAT MCP session contexts."""

    def __call__(self, endpoint: str) -> AbstractAsyncContextManager[NATMCPSession]:
        """Return async context manager for one endpoint session."""


@dataclass(slots=True)
class _NATSessionState:
    """Cached MCP SDK session state for one external server."""

    exit_stack: AsyncExitStack
    session: NATMCPSession
    initialized: bool = False
    last_activity_at: datetime | None = None


class NATMCPTransportAdapter:
    """MCP transport adapter backed by the NAT/MCP Python SDK."""

    def __init__(
        self,
        *,
        session_factory: NATMCPSessionFactory | None = None,
        request_timeout_seconds: float = 10.0,
    ) -> None:
        self._session_factory = session_factory or self._default_session_factory
        self._request_timeout_seconds = request_timeout_seconds
        self._sessions: dict[str, _NATSessionState] = {}

    async def __call__(self, server: ExternalServer, request: JSONObject) -> JSONObject:
        """Dispatch one JSON-RPC request through a stateful NAT session."""
        method = request.get("method")
        if not isinstance(method, str):
            msg = "Invalid JSON-RPC request method"
            raise MCPTransportError(msg, category="invalid_payload")

        request_id = request.get("id")
        if request_id is None:
            msg = "Missing JSON-RPC request id"
            raise MCPTransportError(msg, category="invalid_payload")

        try:
            state = await self._session_state(server)
            state.last_activity_at = datetime.now(UTC)
            return await self._dispatch(state, request, method, request_id)
        except MCPTransportError as exc:
            if exc.category in {"network_timeout", "http_status", "transport_error"}:
                await self.invalidate_session(server.name)
            raise
        except Exception as exc:  # noqa: BLE001
            if self._is_mcp_rpc_error(exc):
                return self._jsonrpc_response(
                    request_id=request_id,
                    payload={"message": str(exc)},
                    field="error",
                )
            mapped = self._map_exception(exc)
            if mapped.category in {"network_timeout", "http_status", "transport_error"}:
                await self.invalidate_session(server.name)
            raise mapped from exc

    async def _dispatch(
        self,
        state: _NATSessionState,
        request: JSONObject,
        method: str,
        request_id: JSONValue,
    ) -> JSONObject:
        if method == "initialize":
            result = await state.session.initialize()
            state.initialized = True
            return self._jsonrpc_response(
                request_id=request_id,
                payload=self._to_json_object(result),
                field="result",
            )

        if method == "notifications/initialized":
            await self._ensure_initialized(state)
            await self._send_initialized_notification(state.session)
            return self._jsonrpc_response(request_id=request_id, payload={}, field="result")

        if method == "tools/call":
            await self._ensure_initialized(state)
            params = self._request_params(request)
            tool_name = params.get("name")
            if not isinstance(tool_name, str):
                msg = "Invalid tools/call payload: expected string tool name"
                raise MCPTransportError(msg, category="invalid_payload")
            arguments = params.get("arguments")
            if arguments is None:
                tool_args: dict[str, Any] | None = {}
            elif isinstance(arguments, dict):
                tool_args = cast(dict[str, Any], arguments)
            else:
                msg = "Invalid tools/call payload: expected object arguments"
                raise MCPTransportError(msg, category="invalid_payload")
            result = await state.session.call_tool(tool_name, tool_args)
            return self._jsonrpc_response(
                request_id=request_id,
                payload=self._to_json_object(result),
                field="result",
            )

        if method == "resources/read":
            await self._ensure_initialized(state)
            params = self._request_params(request)
            uri = params.get("uri")
            if not isinstance(uri, str):
                msg = "Invalid resources/read payload: expected string uri"
                raise MCPTransportError(msg, category="invalid_payload")
            from pydantic import AnyUrl

            result = await state.session.read_resource(AnyUrl(uri))
            return self._jsonrpc_response(
                request_id=request_id,
                payload=self._to_json_object(result),
                field="result",
            )

        msg = f"Unsupported MCP method: {method}"
        raise MCPTransportError(msg, category="invalid_payload")

    async def _ensure_initialized(self, state: _NATSessionState) -> None:
        if state.initialized:
            return
        await state.session.initialize()
        state.initialized = True

    async def _send_initialized_notification(self, session: NATMCPSession) -> None:
        from mcp import types as mcp_types

        notification = mcp_types.InitializedNotification(
            method="notifications/initialized",
            params=None,
        )
        await session.send_notification(notification)

    def _request_params(self, request: JSONObject) -> JSONObject:
        params = request.get("params")
        if params is None:
            return {}
        if not isinstance(params, dict):
            msg = "Invalid JSON-RPC params payload"
            raise MCPTransportError(msg, category="invalid_payload")
        if not all(isinstance(key, str) for key in params):
            msg = "Invalid JSON-RPC params keys"
            raise MCPTransportError(msg, category="invalid_payload")
        return params

    async def _session_state(self, server: ExternalServer) -> _NATSessionState:
        existing = self._sessions.get(server.name)
        if existing is not None:
            return existing

        endpoint = self._mcp_endpoint(server.url)
        exit_stack = AsyncExitStack()
        session_context = self._session_factory(endpoint)
        session = await exit_stack.enter_async_context(session_context)
        created = _NATSessionState(
            exit_stack=exit_stack,
            session=session,
            initialized=False,
            last_activity_at=datetime.now(UTC),
        )
        self._sessions[server.name] = created
        return created

    async def invalidate_session(self, server_name: str) -> bool:
        """Invalidate one cached server session."""
        state = self._sessions.pop(server_name, None)
        if state is not None:
            await state.exit_stack.aclose()
            return True
        return False

    def session_diagnostics(self, server_name: str) -> AdapterSessionDiagnostics:
        """Return non-sensitive diagnostics for one server session."""
        state = self._sessions.get(server_name)
        if state is None:
            return AdapterSessionDiagnostics(
                active=False,
                initialized=False,
                last_activity_at=None,
            )
        return AdapterSessionDiagnostics(
            active=True,
            initialized=state.initialized,
            last_activity_at=state.last_activity_at,
        )

    def _default_session_factory(
        self,
        endpoint: str,
    ) -> AbstractAsyncContextManager[NATMCPSession]:
        return self._streamable_http_session(endpoint)

    @asynccontextmanager
    async def _streamable_http_session(self, endpoint: str) -> AsyncIterator[NATMCPSession]:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        timeout = timedelta(seconds=self._request_timeout_seconds)
        async with streamablehttp_client(url=endpoint, timeout=timeout) as (read, write, _):
            async with ClientSession(read, write) as session:
                yield cast(NATMCPSession, session)

    @staticmethod
    def _mcp_endpoint(base_url: str) -> str:
        trimmed = base_url.rstrip("/")
        if trimmed.endswith("/mcp"):
            return trimmed
        return f"{trimmed}/mcp"

    @staticmethod
    def _jsonrpc_response(
        *,
        request_id: JSONValue,
        payload: JSONValue,
        field: Literal["result", "error"],
    ) -> JSONObject:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            field: payload,
        }

    @staticmethod
    def _to_json_object(value: Any) -> JSONObject:
        if hasattr(value, "model_dump"):
            payload = value.model_dump(mode="json", exclude_none=True)
        else:
            payload = value
        if not isinstance(payload, dict):
            msg = "Invalid MCP SDK response payload"
            raise MCPTransportError(msg, category="invalid_payload")
        if not all(isinstance(key, str) for key in payload):
            msg = "Invalid MCP SDK response keys"
            raise MCPTransportError(msg, category="invalid_payload")
        return cast(JSONObject, payload)

    @staticmethod
    def _is_mcp_rpc_error(exc: Exception) -> bool:
        try:
            from mcp.shared.exceptions import McpError

            return isinstance(exc, McpError)
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _map_exception(exc: Exception) -> MCPTransportError:
        if isinstance(exc, MCPTransportError):
            return exc
        if isinstance(exc, httpx.TimeoutException):
            return MCPTransportError(str(exc), category="network_timeout")
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            return MCPTransportError(f"http status {status_code}", category="http_status")
        if isinstance(exc, httpx.HTTPError):
            return MCPTransportError(str(exc), category="transport_error")
        if isinstance(exc, ValueError | TypeError):
            return MCPTransportError(str(exc), category="invalid_payload")
        return MCPTransportError(str(exc), category="transport_error")


def create_nat_mcp_transport_adapter() -> MCPTransport | None:
    """Create NAT MCP transport adapter when MCP SDK is available."""
    try:
        import mcp.client.session  # noqa: F401
        import mcp.client.streamable_http  # noqa: F401
    except Exception:  # noqa: BLE001
        return None
    return NATMCPTransportAdapter()


class MCPClientManager:
    """Track external MCP server availability and retry policy."""

    def __init__(
        self,
        *,
        probe: HealthProbe | None = None,
        transport: MCPTransport | None = None,
        transport_adapter: MCPTransport | None = None,
        max_backoff_seconds: int = 8,
        unreachable_after: int = 3,
        max_initialization_age_seconds: int | None = 300,
        max_invocation_events: int = 500,
    ) -> None:
        self._servers: dict[str, ExternalServer] = {}
        self._events: list[ConnectionEvent] = []
        self._invocation_events: deque[MCPInvocationEvent] = deque(
            maxlen=max(1, max_invocation_events)
        )
        self._probe = probe
        self._transport = transport
        self._transport_adapter = transport_adapter
        self._max_backoff_seconds = max_backoff_seconds
        self._unreachable_after = unreachable_after
        self._max_initialization_age_seconds = max_initialization_age_seconds

    def register(self, name: str, url: str) -> ExternalServer:
        """Register or replace a server definition."""
        server = ExternalServer(name=name, url=url)
        self._servers[name] = server
        return server

    def unregister(self, name: str) -> None:
        """Remove one server."""
        self._servers.pop(name, None)

    def get(self, name: str) -> ExternalServer | None:
        """Fetch one registered server."""
        return self._servers.get(name)

    def list_servers(self) -> list[ExternalServer]:
        """List known servers by name."""
        return sorted(self._servers.values(), key=lambda item: item.name)

    def list_events(
        self,
        *,
        server: str | None = None,
        correlation_id: str | None = None,
        limit: int | None = None,
    ) -> list[ConnectionEvent]:
        """List connection status transition events with optional filtering."""
        events = [
            event
            for event in self._events
            if (server is None or event.server == server)
            and (correlation_id is None or event.correlation_id == correlation_id)
        ]
        if limit is not None:
            if limit <= 0:
                return []
            events = events[-limit:]
        return events

    def list_invocation_events(
        self,
        *,
        server: str | None = None,
        method: str | None = None,
        request_id: str | None = None,
        limit: int | None = None,
    ) -> list[MCPInvocationEvent]:
        """List invocation lifecycle events (bounded retention) with optional filtering."""
        events = [
            event
            for event in self._invocation_events
            if (server is None or event.server == server)
            and (method is None or event.method == method)
            and (request_id is None or event.request_id == request_id)
        ]
        if limit is not None:
            if limit <= 0:
                return []
            events = events[-limit:]
        return events

    def choose_server(self, preferred: list[str] | None = None) -> ExternalServer | None:
        """Choose best available server with healthy-first policy."""
        ordered = self._order_candidates(preferred)
        for candidate in ordered:
            if candidate.status is ServerStatus.HEALTHY:
                return candidate
        for candidate in ordered:
            if candidate.status is ServerStatus.DEGRADED:
                return candidate
        return None

    def should_retry(self, name: str, *, now: datetime | None = None) -> bool:
        """Check whether retry window is open for a server."""
        server = self._servers.get(name)
        if server is None:
            return False
        if server.next_retry_at is None:
            return True
        current = now or datetime.now(UTC)
        return current >= server.next_retry_at

    async def health_check_server(self, name: str) -> ExternalServer | None:
        """Run health check for one server and update status/backoff."""
        server = self._servers.get(name)
        if server is None:
            return None
        if not self.should_retry(name):
            return server
        probe = self._probe or self._default_probe
        healthy, error = await probe(server)
        self.record_check_result(
            name,
            healthy=healthy,
            error=error,
            error_category="health_check" if not healthy else None,
        )
        return self._servers.get(name)

    async def health_check_all(self) -> list[ExternalServer]:
        """Run health checks for all retry-eligible servers."""
        results: list[ExternalServer] = []
        for name in sorted(self._servers):
            checked = await self.health_check_server(name)
            if checked is not None:
                results.append(checked)
        return results

    async def initialize_server(
        self,
        name: str,
        *,
        force: bool = False,
        correlation_id: str | None = None,
    ) -> ExternalServer | None:
        """Perform MCP initialize handshake for one server."""
        server = self._servers.get(name)
        if server is None:
            return None
        if server.initialized and not force:
            return server

        transport = self._resolve_transport()
        request_id = str(uuid4())
        initialize_request = self._build_request(
            "initialize",
            request_id=request_id,
            params={
                "protocolVersion": "2025-11-25",
                "clientInfo": {"name": "att", "version": "0.1.0"},
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
            },
        )
        try:
            response = await transport(server, initialize_request)
        except Exception as exc:  # noqa: BLE001
            server.initialized = False
            server.protocol_version = None
            self.record_check_result(
                name,
                healthy=False,
                error=str(exc),
                error_category=self._error_category_from_exception(exc),
                correlation_id=correlation_id,
            )
            return self._servers.get(name)

        rpc_error = self._extract_error(response)
        if rpc_error is not None:
            server.initialized = False
            server.protocol_version = None
            self.record_check_result(
                name,
                healthy=False,
                error=f"rpc error: {rpc_error}",
                error_category="rpc_error",
                correlation_id=correlation_id,
            )
            return self._servers.get(name)

        result = response.get("result")
        if not isinstance(result, dict):
            server.initialized = False
            server.protocol_version = None
            self.record_check_result(
                name,
                healthy=False,
                error="rpc error: invalid initialize result",
                error_category="invalid_payload",
                correlation_id=correlation_id,
            )
            return self._servers.get(name)

        protocol = result.get("protocolVersion")
        server.protocol_version = protocol if isinstance(protocol, str) else None
        initialized_at = datetime.now(UTC)
        server.initialized = True
        server.last_initialized_at = initialized_at
        server.initialization_expires_at = self._compute_initialization_expiry(initialized_at)
        server.capability_snapshot = CapabilitySnapshot(
            protocol_version=server.protocol_version,
            server_info=self._as_json_object(result.get("serverInfo")),
            capabilities=self._as_json_object(result.get("capabilities")),
            captured_at=initialized_at,
        )
        self.record_check_result(name, healthy=True, correlation_id=correlation_id)

        initialized_notification = self._build_request(
            "notifications/initialized",
            request_id=str(uuid4()),
            params={},
        )
        try:
            await transport(server, initialized_notification)
        except Exception as exc:  # noqa: BLE001
            server.initialized = False
            self.record_check_result(
                name,
                healthy=False,
                error=str(exc),
                error_category=self._error_category_from_exception(exc),
                correlation_id=correlation_id,
            )
        return self._servers.get(name)

    async def initialize_all(self, *, force: bool = False) -> list[ExternalServer]:
        """Perform initialize handshake for all servers."""
        initialized: list[ExternalServer] = []
        for name in sorted(self._servers):
            server = await self.initialize_server(name, force=force)
            if server is not None:
                initialized.append(server)
        return initialized

    async def connect_server(self, name: str, *, force: bool = False) -> ExternalServer | None:
        """Run health check + initialize handshake for one server."""
        checked = await self.health_check_server(name)
        if checked is None:
            return None
        if checked.status is ServerStatus.UNREACHABLE and not force:
            return checked
        return await self.initialize_server(name, force=force)

    async def connect_all(self, *, force: bool = False) -> list[ExternalServer]:
        """Run health check + initialize handshake for all servers."""
        connected: list[ExternalServer] = []
        for name in sorted(self._servers):
            server = await self.connect_server(name, force=force)
            if server is not None:
                connected.append(server)
        return connected

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, JSONValue] | None = None,
        *,
        preferred: list[str] | None = None,
    ) -> MCPInvocationResult:
        """Invoke an MCP tool with fallback across eligible servers."""
        params: JSONObject = {
            "name": tool_name,
            "arguments": arguments or {},
        }
        return await self._invoke("tools/call", params, preferred=preferred)

    async def read_resource(
        self,
        uri: str,
        *,
        preferred: list[str] | None = None,
    ) -> MCPInvocationResult:
        """Read an MCP resource with fallback across eligible servers."""
        params: JSONObject = {"uri": uri}
        return await self._invoke("resources/read", params, preferred=preferred)

    def record_check_result(
        self,
        name: str,
        *,
        healthy: bool,
        error: str | None = None,
        error_category: ErrorCategory | None = None,
        checked_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Apply one health check result and update retry metadata."""
        server = self._servers.get(name)
        if server is None:
            return
        when = checked_at or datetime.now(UTC)
        old_status = server.status
        if healthy:
            server.status = ServerStatus.HEALTHY
            server.last_error = None
            server.last_error_category = None
            server.retry_count = 0
            server.next_retry_at = None
        else:
            server.initialized = False
            server.initialization_expires_at = None
            server.retry_count += 1
            if server.retry_count >= self._unreachable_after:
                server.status = ServerStatus.UNREACHABLE
            else:
                server.status = ServerStatus.DEGRADED
            server.last_error = error or "health check failed"
            server.last_error_category = error_category or "unknown"
            backoff_seconds = min(
                2 ** (server.retry_count - 1),
                self._max_backoff_seconds,
            )
            server.next_retry_at = when + timedelta(seconds=backoff_seconds)
        server.last_checked_at = when
        if server.status is not old_status:
            self._events.append(
                ConnectionEvent(
                    server=name,
                    from_status=old_status,
                    to_status=server.status,
                    reason=server.last_error or "healthy",
                    timestamp=when,
                    correlation_id=correlation_id,
                )
            )

    def mark_degraded(self, name: str, *, reason: str = "manual degrade") -> None:
        """Manual degrade marker for one server."""
        self.record_check_result(name, healthy=False, error=reason)

    def mark_healthy(self, name: str) -> None:
        """Manual healthy marker for one server."""
        self.record_check_result(name, healthy=True)

    def supports_adapter_session_controls(self) -> bool:
        """Whether adapter-specific invalidate/refresh controls are available."""
        return self._adapter_with_session_controls() is not None

    def adapter_session_diagnostics(self, name: str) -> AdapterSessionDiagnostics | None:
        """Return adapter session diagnostics for one server when supported."""
        adapter = self._adapter_with_session_controls()
        if adapter is None:
            return None
        return adapter.session_diagnostics(name)

    def list_adapter_sessions(self) -> list[AdapterSessionStatus]:
        """List adapter session status across all registered servers."""
        adapter = self._adapter_with_session_controls()
        if adapter is None:
            return []
        statuses: list[AdapterSessionStatus] = []
        for server in self.list_servers():
            diagnostics = adapter.session_diagnostics(server.name)
            statuses.append(
                AdapterSessionStatus(
                    server=server.name,
                    active=diagnostics.active,
                    initialized=diagnostics.initialized,
                    last_activity_at=diagnostics.last_activity_at,
                )
            )
        return statuses

    async def invalidate_adapter_session(self, name: str) -> bool:
        """Invalidate adapter session for one server when supported."""
        adapter = self._adapter_with_session_controls()
        if adapter is None:
            return False
        invalidated = await adapter.invalidate_session(name)
        server = self._servers.get(name)
        if server is not None:
            server.initialized = False
            server.initialization_expires_at = None
        return invalidated

    async def refresh_adapter_session(self, name: str) -> ExternalServer | None:
        """Force refresh adapter session and reinitialize server."""
        server = self._servers.get(name)
        if server is None:
            return None
        await self.invalidate_adapter_session(name)
        return await self.initialize_server(name, force=True)

    async def _invoke(
        self,
        method: str,
        params: JSONObject,
        *,
        preferred: list[str] | None,
    ) -> MCPInvocationResult:
        candidates = self._invocation_candidates(preferred)
        attempts: list[MCPInvocationAttempt] = []
        if not candidates:
            raise MCPInvocationError(
                "No reachable MCP servers are currently available",
                method=method,
                attempts=attempts,
            )

        request_id = str(uuid4())
        request = self._build_request(method, request_id=request_id, params=params)
        transport = self._resolve_transport()
        errors: list[str] = []

        for server in candidates:
            self._record_invocation_event(
                server=server.name,
                method=method,
                request_id=request_id,
                phase="initialize_start",
            )
            initialized = await self.initialize_server(
                server.name,
                force=self._should_force_reinitialize(server),
                correlation_id=request_id,
            )
            if initialized is None:
                self._record_invocation_event(
                    server=server.name,
                    method=method,
                    request_id=request_id,
                    phase="initialize_failure",
                    error="server not found",
                    error_category="initialize_error",
                )
                attempts.append(
                    MCPInvocationAttempt(
                        server=server.name,
                        stage="initialize",
                        success=False,
                        error="server not found",
                        error_category="initialize_error",
                    )
                )
                errors.append(f"{server.name}: server not found")
                continue
            if not initialized.initialized:
                init_error = initialized.last_error or "initialize failed"
                self._record_invocation_event(
                    server=server.name,
                    method=method,
                    request_id=request_id,
                    phase="initialize_failure",
                    error=init_error,
                    error_category=initialized.last_error_category or "initialize_error",
                )
                attempts.append(
                    MCPInvocationAttempt(
                        server=server.name,
                        stage="initialize",
                        success=False,
                        error=init_error,
                        error_category=initialized.last_error_category or "initialize_error",
                    )
                )
                errors.append(f"{server.name}: initialize failed ({init_error})")
                continue
            self._record_invocation_event(
                server=initialized.name,
                method=method,
                request_id=request_id,
                phase="initialize_success",
            )
            attempts.append(
                MCPInvocationAttempt(
                    server=initialized.name,
                    stage="initialize",
                    success=True,
                )
            )
            self._record_invocation_event(
                server=initialized.name,
                method=method,
                request_id=request_id,
                phase="invoke_start",
            )
            try:
                response = await transport(initialized, request)
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                error_category = self._error_category_from_exception(exc)
                self._record_invocation_event(
                    server=initialized.name,
                    method=method,
                    request_id=request_id,
                    phase="invoke_failure",
                    error=message,
                    error_category=error_category,
                )
                self.record_check_result(
                    initialized.name,
                    healthy=False,
                    error=message,
                    error_category=error_category,
                    correlation_id=request_id,
                )
                attempts.append(
                    MCPInvocationAttempt(
                        server=initialized.name,
                        stage="invoke",
                        success=False,
                        error=message,
                        error_category=error_category,
                    )
                )
                errors.append(f"{initialized.name}: {message}")
                continue

            rpc_error = self._extract_error(response)
            if rpc_error is not None:
                invocation_error = f"rpc error: {rpc_error}"
                self._record_invocation_event(
                    server=initialized.name,
                    method=method,
                    request_id=request_id,
                    phase="invoke_failure",
                    error=invocation_error,
                    error_category="rpc_error",
                )
                self.record_check_result(
                    initialized.name,
                    healthy=False,
                    error=invocation_error,
                    error_category="rpc_error",
                    correlation_id=request_id,
                )
                attempts.append(
                    MCPInvocationAttempt(
                        server=initialized.name,
                        stage="invoke",
                        success=False,
                        error=invocation_error,
                        error_category="rpc_error",
                    )
                )
                errors.append(f"{initialized.name}: {invocation_error}")
                continue

            if "result" not in response:
                missing_result = "rpc error: missing result"
                self._record_invocation_event(
                    server=initialized.name,
                    method=method,
                    request_id=request_id,
                    phase="invoke_failure",
                    error=missing_result,
                    error_category="invalid_payload",
                )
                self.record_check_result(
                    initialized.name,
                    healthy=False,
                    error=missing_result,
                    error_category="invalid_payload",
                    correlation_id=request_id,
                )
                attempts.append(
                    MCPInvocationAttempt(
                        server=initialized.name,
                        stage="invoke",
                        success=False,
                        error=missing_result,
                        error_category="invalid_payload",
                    )
                )
                errors.append(f"{initialized.name}: {missing_result}")
                continue

            self._record_invocation_event(
                server=initialized.name,
                method=method,
                request_id=request_id,
                phase="invoke_success",
            )
            attempts.append(
                MCPInvocationAttempt(
                    server=initialized.name,
                    stage="invoke",
                    success=True,
                )
            )
            self.record_check_result(
                initialized.name,
                healthy=True,
                correlation_id=request_id,
            )
            return MCPInvocationResult(
                server=initialized.name,
                method=method,
                request_id=request_id,
                result=response["result"],
                raw_response=response,
            )

        joined = "; ".join(errors) if errors else "unknown invocation failure"
        msg = f"Invocation failed across servers: {joined}"
        raise MCPInvocationError(msg, method=method, attempts=attempts)

    @staticmethod
    def _build_request(method: str, *, request_id: str, params: JSONObject) -> JSONObject:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

    @staticmethod
    def _extract_error(response: JSONObject) -> str | None:
        error_payload = response.get("error")
        if error_payload is None:
            return None
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if isinstance(message, str):
                return message
            code = error_payload.get("code")
            return f"code={code}"
        return str(error_payload)

    @staticmethod
    def _as_json_object(value: JSONValue) -> JSONObject | None:
        if isinstance(value, dict) and all(isinstance(key, str) for key in value):
            return value
        return None

    def _invocation_candidates(self, preferred: list[str] | None) -> list[ExternalServer]:
        ordered = self._order_candidates(preferred)
        healthy = [server for server in ordered if server.status is ServerStatus.HEALTHY]
        degraded = [
            server
            for server in ordered
            if server.status is ServerStatus.DEGRADED and self.should_retry(server.name)
        ]
        unreachable = [
            server
            for server in ordered
            if server.status is ServerStatus.UNREACHABLE and self.should_retry(server.name)
        ]
        return [*healthy, *degraded, *unreachable]

    def _should_force_reinitialize(self, server: ExternalServer) -> bool:
        if not server.initialized:
            return False
        if server.status is not ServerStatus.HEALTHY:
            return True
        expiry = server.initialization_expires_at
        if expiry is not None and datetime.now(UTC) >= expiry:
            return True
        return False

    def _compute_initialization_expiry(self, initialized_at: datetime) -> datetime | None:
        max_age = self._max_initialization_age_seconds
        if max_age is None:
            return None
        return initialized_at + timedelta(seconds=max(0, max_age))

    def _record_invocation_event(
        self,
        *,
        server: str,
        method: str,
        request_id: str,
        phase: InvocationPhase,
        error: str | None = None,
        error_category: ErrorCategory | None = None,
    ) -> None:
        self._invocation_events.append(
            MCPInvocationEvent(
                server=server,
                method=method,
                request_id=request_id,
                phase=phase,
                timestamp=datetime.now(UTC),
                error=error,
                error_category=error_category,
            )
        )

    def _resolve_transport(self) -> MCPTransport:
        return self._transport_adapter or self._transport or self._default_transport

    def _adapter_with_session_controls(self) -> NATMCPTransportAdapter | None:
        adapter = self._transport_adapter
        if isinstance(adapter, NATMCPTransportAdapter):
            return adapter
        return None

    @staticmethod
    async def _default_probe(server: ExternalServer) -> tuple[bool, str | None]:
        """Default HTTP health probe against `/health`."""
        health_url = f"{server.url.rstrip('/')}/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
            if response.status_code < 400:
                return True, None
            return False, f"http {response.status_code}"
        except httpx.HTTPError as exc:
            return False, str(exc)

    @staticmethod
    async def _default_transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        """Default Streamable HTTP JSON-RPC transport."""
        endpoint = f"{server.url.rstrip('/')}/mcp"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(endpoint, json=request)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MCPTransportError(str(exc), category="network_timeout") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            message = f"http status {status_code}"
            raise MCPTransportError(message, category="http_status") from exc
        except httpx.HTTPError as exc:
            raise MCPTransportError(str(exc), category="transport_error") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            msg = "Invalid JSON-RPC response payload"
            raise MCPTransportError(msg, category="invalid_payload") from exc
        if not isinstance(payload, dict):
            msg = "Invalid JSON-RPC response payload"
            raise MCPTransportError(msg, category="invalid_payload")
        if not all(isinstance(key, str) for key in payload):
            msg = "Invalid JSON-RPC response keys"
            raise MCPTransportError(msg, category="invalid_payload")
        return cast(JSONObject, payload)

    def _order_candidates(self, preferred: list[str] | None) -> list[ExternalServer]:
        if not preferred:
            return self.list_servers()
        preferred_set = set(preferred)
        prioritized = [self._servers[name] for name in preferred if name in self._servers]
        others = [server for server in self.list_servers() if server.name not in preferred_set]
        return [*prioritized, *others]

    @staticmethod
    def _error_category_from_exception(exc: Exception) -> ErrorCategory:
        if isinstance(exc, MCPTransportError):
            return exc.category
        if isinstance(exc, httpx.TimeoutException):
            return "network_timeout"
        if isinstance(exc, httpx.HTTPStatusError):
            return "http_status"
        if isinstance(exc, httpx.HTTPError):
            return "transport_error"
        return "transport_error"
