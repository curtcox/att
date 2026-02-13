"""ATT MCP client management with health/backoff handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal, Protocol, cast
from uuid import uuid4

import httpx

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]


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
    retry_count: int = 0
    last_checked_at: datetime | None = None
    next_retry_at: datetime | None = None
    initialized: bool = False
    protocol_version: str | None = None
    last_initialized_at: datetime | None = None
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


class HealthProbe(Protocol):
    """Async probe protocol for MCP health checks."""

    async def __call__(self, server: ExternalServer) -> tuple[bool, str | None]:
        """Return (healthy, error_message)."""


class MCPTransport(Protocol):
    """Async transport protocol for MCP JSON-RPC requests."""

    async def __call__(self, server: ExternalServer, request: JSONObject) -> JSONObject:
        """Send request to one server and return JSON object response."""


class MCPClientManager:
    """Track external MCP server availability and retry policy."""

    def __init__(
        self,
        *,
        probe: HealthProbe | None = None,
        transport: MCPTransport | None = None,
        max_backoff_seconds: int = 8,
        unreachable_after: int = 3,
    ) -> None:
        self._servers: dict[str, ExternalServer] = {}
        self._events: list[ConnectionEvent] = []
        self._probe = probe
        self._transport = transport
        self._max_backoff_seconds = max_backoff_seconds
        self._unreachable_after = unreachable_after

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

    def list_events(self) -> list[ConnectionEvent]:
        """List connection status transition events."""
        return list(self._events)

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
        self.record_check_result(name, healthy=healthy, error=error)
        return self._servers.get(name)

    async def health_check_all(self) -> list[ExternalServer]:
        """Run health checks for all retry-eligible servers."""
        results: list[ExternalServer] = []
        for name in sorted(self._servers):
            checked = await self.health_check_server(name)
            if checked is not None:
                results.append(checked)
        return results

    async def initialize_server(self, name: str, *, force: bool = False) -> ExternalServer | None:
        """Perform MCP initialize handshake for one server."""
        server = self._servers.get(name)
        if server is None:
            return None
        if server.initialized and not force:
            return server

        transport = self._transport or self._default_transport
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
            self.record_check_result(name, healthy=False, error=str(exc))
            return self._servers.get(name)

        rpc_error = self._extract_error(response)
        if rpc_error is not None:
            server.initialized = False
            server.protocol_version = None
            self.record_check_result(name, healthy=False, error=f"rpc error: {rpc_error}")
            return self._servers.get(name)

        result = response.get("result")
        if not isinstance(result, dict):
            server.initialized = False
            server.protocol_version = None
            self.record_check_result(
                name, healthy=False, error="rpc error: invalid initialize result"
            )
            return self._servers.get(name)

        protocol = result.get("protocolVersion")
        server.protocol_version = protocol if isinstance(protocol, str) else None
        initialized_at = datetime.now(UTC)
        server.initialized = True
        server.last_initialized_at = initialized_at
        server.capability_snapshot = CapabilitySnapshot(
            protocol_version=server.protocol_version,
            server_info=self._as_json_object(result.get("serverInfo")),
            capabilities=self._as_json_object(result.get("capabilities")),
            captured_at=initialized_at,
        )
        self.record_check_result(name, healthy=True)

        initialized_notification = self._build_request(
            "notifications/initialized",
            request_id=str(uuid4()),
            params={},
        )
        try:
            await transport(server, initialized_notification)
        except Exception as exc:  # noqa: BLE001
            server.initialized = False
            self.record_check_result(name, healthy=False, error=str(exc))
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
        checked_at: datetime | None = None,
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
            server.retry_count = 0
            server.next_retry_at = None
        else:
            server.initialized = False
            server.retry_count += 1
            if server.retry_count >= self._unreachable_after:
                server.status = ServerStatus.UNREACHABLE
            else:
                server.status = ServerStatus.DEGRADED
            server.last_error = error or "health check failed"
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
                )
            )

    def mark_degraded(self, name: str, *, reason: str = "manual degrade") -> None:
        """Manual degrade marker for one server."""
        self.record_check_result(name, healthy=False, error=reason)

    def mark_healthy(self, name: str) -> None:
        """Manual healthy marker for one server."""
        self.record_check_result(name, healthy=True)

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
        transport = self._transport or self._default_transport
        errors: list[str] = []

        for server in candidates:
            initialized = await self.initialize_server(server.name)
            if initialized is None:
                attempts.append(
                    MCPInvocationAttempt(
                        server=server.name,
                        stage="initialize",
                        success=False,
                        error="server not found",
                    )
                )
                errors.append(f"{server.name}: server not found")
                continue
            if not initialized.initialized:
                init_error = initialized.last_error or "initialize failed"
                attempts.append(
                    MCPInvocationAttempt(
                        server=server.name,
                        stage="initialize",
                        success=False,
                        error=init_error,
                    )
                )
                errors.append(f"{server.name}: initialize failed ({init_error})")
                continue
            attempts.append(
                MCPInvocationAttempt(
                    server=initialized.name,
                    stage="initialize",
                    success=True,
                )
            )
            try:
                response = await transport(initialized, request)
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                self.record_check_result(initialized.name, healthy=False, error=message)
                attempts.append(
                    MCPInvocationAttempt(
                        server=initialized.name,
                        stage="invoke",
                        success=False,
                        error=message,
                    )
                )
                errors.append(f"{initialized.name}: {message}")
                continue

            rpc_error = self._extract_error(response)
            if rpc_error is not None:
                invocation_error = f"rpc error: {rpc_error}"
                self.record_check_result(
                    initialized.name,
                    healthy=False,
                    error=invocation_error,
                )
                attempts.append(
                    MCPInvocationAttempt(
                        server=initialized.name,
                        stage="invoke",
                        success=False,
                        error=invocation_error,
                    )
                )
                errors.append(f"{initialized.name}: {invocation_error}")
                continue

            if "result" not in response:
                missing_result = "rpc error: missing result"
                self.record_check_result(initialized.name, healthy=False, error=missing_result)
                attempts.append(
                    MCPInvocationAttempt(
                        server=initialized.name,
                        stage="invoke",
                        success=False,
                        error=missing_result,
                    )
                )
                errors.append(f"{initialized.name}: {missing_result}")
                continue

            attempts.append(
                MCPInvocationAttempt(
                    server=initialized.name,
                    stage="invoke",
                    success=True,
                )
            )
            self.record_check_result(initialized.name, healthy=True)
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
        except httpx.HTTPError as exc:
            raise RuntimeError(str(exc)) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            msg = "Invalid JSON-RPC response payload"
            raise RuntimeError(msg)
        if not all(isinstance(key, str) for key in payload):
            msg = "Invalid JSON-RPC response keys"
            raise RuntimeError(msg)
        return cast(JSONObject, payload)

    def _order_candidates(self, preferred: list[str] | None) -> list[ExternalServer]:
        if not preferred:
            return self.list_servers()
        preferred_set = set(preferred)
        prioritized = [self._servers[name] for name in preferred if name in self._servers]
        others = [server for server in self.list_servers() if server.name not in preferred_set]
        return [*prioritized, *others]
