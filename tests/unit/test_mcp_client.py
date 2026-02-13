from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from att.mcp.client import (
    ExternalServer,
    JSONObject,
    MCPClientManager,
    MCPInvocationError,
    MCPTransportError,
    NATMCPTransportAdapter,
    ServerStatus,
)


@pytest.mark.asyncio
async def test_health_check_probe_updates_status_and_logs_transition() -> None:
    async def flaky_probe(_: object) -> tuple[bool, str | None]:
        return False, "timeout"

    manager = MCPClientManager(probe=flaky_probe, unreachable_after=2)
    manager.register("codex", "http://codex.local")

    await manager.health_check_server("codex")
    server = manager.get("codex")
    assert server is not None
    assert server.status is ServerStatus.DEGRADED
    assert server.retry_count == 1
    assert server.last_error == "timeout"
    server.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)

    await manager.health_check_server("codex")
    server = manager.get("codex")
    assert server is not None
    assert server.status is ServerStatus.UNREACHABLE
    assert server.retry_count == 2

    events = manager.list_events()
    assert len(events) == 2
    assert events[0].to_status is ServerStatus.DEGRADED
    assert events[1].to_status is ServerStatus.UNREACHABLE


@pytest.mark.asyncio
async def test_health_check_recovery_resets_backoff() -> None:
    states = [(False, "temporary"), (True, None)]

    async def toggled_probe(_: object) -> tuple[bool, str | None]:
        return states.pop(0)

    manager = MCPClientManager(probe=toggled_probe)
    manager.register("github", "http://github.local")

    await manager.health_check_server("github")
    degraded = manager.get("github")
    assert degraded is not None
    assert degraded.status is ServerStatus.DEGRADED
    assert degraded.next_retry_at is not None

    manager.record_check_result("github", healthy=True)
    recovered = manager.get("github")
    assert recovered is not None
    assert recovered.status is ServerStatus.HEALTHY
    assert recovered.retry_count == 0
    assert recovered.next_retry_at is None


@pytest.mark.asyncio
async def test_should_retry_observes_next_retry_window() -> None:
    manager = MCPClientManager()
    manager.register("terminal", "http://terminal.local")

    now = datetime.now(UTC)
    manager.record_check_result(
        "terminal",
        healthy=False,
        error="down",
        checked_at=now,
    )

    assert manager.should_retry("terminal", now=now) is False
    assert manager.should_retry("terminal", now=now + timedelta(seconds=1)) is True


def test_choose_server_prefers_healthy_then_degraded() -> None:
    manager = MCPClientManager()
    manager.register("a", "http://a.local")
    manager.register("b", "http://b.local")

    manager.record_check_result("a", healthy=False, error="slow")

    selected = manager.choose_server()
    assert selected is not None
    assert selected.name == "b"

    manager.record_check_result("b", healthy=False, error="down")
    fallback = manager.choose_server(preferred=["a", "b"])
    assert fallback is not None
    assert fallback.name == "a"


@pytest.mark.asyncio
async def test_invoke_tool_fails_over_to_next_server() -> None:
    calls: list[tuple[str, str]] = []

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        calls.append((server.name, method))
        from_server = server.name
        if from_server == "primary":
            raise RuntimeError("connect timeout")
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True, "method": str(request.get("method", ""))},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")

    result = await manager.invoke_tool(
        "att.project.list",
        {"limit": 10},
        preferred=["primary", "backup"],
    )
    assert result.server == "backup"
    assert result.method == "tools/call"
    assert isinstance(result.result, dict)
    assert result.result["ok"] is True
    assert calls[0] == ("primary", "initialize")
    assert calls[-1] == ("backup", "tools/call")

    primary = manager.get("primary")
    backup = manager.get("backup")
    assert primary is not None
    assert backup is not None
    assert primary.status is ServerStatus.DEGRADED
    assert backup.status is ServerStatus.HEALTHY
    assert primary.initialized is False
    assert backup.initialized is True


@pytest.mark.asyncio
async def test_read_resource_fallback_on_rpc_error() -> None:
    calls: list[tuple[str, str]] = []

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        calls.append((server.name, method))
        from_server = server.name
        if from_server == "primary":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "error": {"message": "rpc down"},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"uri": "att://projects"},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("primary", "http://primary.local")
    manager.register("secondary", "http://secondary.local")

    result = await manager.read_resource(
        "att://projects",
        preferred=["primary", "secondary"],
    )
    assert result.server == "secondary"
    assert result.method == "resources/read"
    assert isinstance(result.result, dict)
    assert result.result["uri"] == "att://projects"
    assert calls[0] == ("primary", "initialize")
    assert calls[-1] == ("secondary", "resources/read")


@pytest.mark.asyncio
async def test_invoke_tool_raises_when_no_servers_available() -> None:
    manager = MCPClientManager()
    with pytest.raises(MCPInvocationError) as exc_info:
        await manager.invoke_tool("att.project.list")
    assert exc_info.value.method == "tools/call"
    assert exc_info.value.attempts == []


@pytest.mark.asyncio
async def test_invoke_tool_error_contains_structured_attempt_trace() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if server.name == "primary":
            raise RuntimeError("primary down")
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "error": {"message": "rpc failure"},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")

    with pytest.raises(MCPInvocationError) as exc_info:
        await manager.invoke_tool("att.project.list", preferred=["primary", "backup"])

    error = exc_info.value
    assert error.method == "tools/call"
    assert len(error.attempts) == 3
    assert error.attempts[0].server == "primary"
    assert error.attempts[0].stage == "initialize"
    assert error.attempts[0].success is False
    assert error.attempts[0].error == "primary down"
    assert error.attempts[0].error_category == "transport_error"
    assert error.attempts[1].server == "backup"
    assert error.attempts[1].stage == "initialize"
    assert error.attempts[1].success is True
    assert error.attempts[1].error_category is None
    assert error.attempts[2].server == "backup"
    assert error.attempts[2].stage == "invoke"
    assert error.attempts[2].success is False
    assert error.attempts[2].error == "rpc error: rpc failure"
    assert error.attempts[2].error_category == "rpc_error"


@pytest.mark.asyncio
async def test_invoke_tool_reinitializes_when_initialization_is_stale() -> None:
    calls: list[str] = []

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        calls.append(method)
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True},
        }

    manager = MCPClientManager(transport=transport, max_initialization_age_seconds=0)
    manager.register("codex", "http://codex.local")

    await manager.initialize_server("codex")
    result = await manager.invoke_tool("att.project.list")

    assert result.server == "codex"
    assert calls == [
        "initialize",
        "notifications/initialized",
        "initialize",
        "notifications/initialized",
        "tools/call",
    ]
    server = manager.get("codex")
    assert server is not None
    assert server.initialization_expires_at is not None


@pytest.mark.asyncio
async def test_invoke_tool_transport_error_category_http_status() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        raise MCPTransportError("http status 503", category="http_status")

    manager = MCPClientManager(transport=transport)
    manager.register("codex", "http://codex.local")

    with pytest.raises(MCPInvocationError) as exc_info:
        await manager.invoke_tool("att.project.list")

    error = exc_info.value
    assert len(error.attempts) == 2
    assert error.attempts[1].stage == "invoke"
    assert error.attempts[1].error_category == "http_status"
    server = manager.get("codex")
    assert server is not None
    assert server.last_error_category == "http_status"


@pytest.mark.asyncio
async def test_invoke_tool_mixed_state_cluster_recovers_in_preferred_order() -> None:
    calls: list[tuple[str, str]] = []

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        calls.append((server.name, method))
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        if server.name == "primary":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "error": {"message": "rpc failure"},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True, "served_by": server.name},
        }

    manager = MCPClientManager(transport=transport, max_initialization_age_seconds=None)
    manager.register("primary", "http://primary.local")
    manager.register("recovered", "http://recovered.local")
    manager.register("degraded", "http://degraded.local")

    primary = manager.get("primary")
    assert primary is not None
    primary.status = ServerStatus.HEALTHY
    primary.initialized = True
    primary.last_initialized_at = datetime.now(UTC)
    primary.initialization_expires_at = datetime.now(UTC) + timedelta(seconds=60)

    recovered = manager.get("recovered")
    assert recovered is not None
    recovered.status = ServerStatus.HEALTHY
    recovered.initialized = False

    manager.record_check_result("degraded", healthy=False, error="down")
    degraded = manager.get("degraded")
    assert degraded is not None
    degraded.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)

    result = await manager.invoke_tool(
        "att.project.list",
        preferred=["primary", "recovered", "degraded"],
    )

    assert result.server == "recovered"
    assert calls[0] == ("primary", "tools/call")
    assert calls[1] == ("recovered", "initialize")
    assert calls[2] == ("recovered", "notifications/initialized")
    assert calls[3] == ("recovered", "tools/call")
    assert ("degraded", "initialize") not in calls
    updated_primary = manager.get("primary")
    updated_recovered = manager.get("recovered")
    assert updated_primary is not None
    assert updated_recovered is not None
    assert updated_primary.status is ServerStatus.DEGRADED
    assert updated_recovered.status is ServerStatus.HEALTHY
    assert updated_recovered.initialized is True


@pytest.mark.asyncio
async def test_invocation_events_emitted_in_order_for_fallback() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if server.name == "primary":
            raise RuntimeError("primary unavailable")
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")

    result = await manager.invoke_tool("att.project.list", preferred=["primary", "backup"])
    assert result.server == "backup"

    events = manager.list_invocation_events()
    phases = [event.phase for event in events]
    assert phases == [
        "initialize_start",
        "initialize_failure",
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    servers = [event.server for event in events]
    assert servers == ["primary", "primary", "backup", "backup", "backup", "backup"]
    request_ids = {event.request_id for event in events}
    assert len(request_ids) == 1


@pytest.mark.asyncio
async def test_invocation_events_retention_is_bounded() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True},
        }

    manager = MCPClientManager(transport=transport, max_invocation_events=3)
    manager.register("codex", "http://codex.local")

    await manager.invoke_tool("att.project.list")

    events = manager.list_invocation_events()
    assert len(events) == 3
    assert [event.phase for event in events] == [
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]


@pytest.mark.asyncio
async def test_initialize_server_updates_state_on_success() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {
                    "protocolVersion": "2025-11-25",
                    "serverInfo": {"name": "codex", "version": "1.0.0"},
                    "capabilities": {"tools": {}, "resources": {}},
                },
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("codex", "http://codex.local")

    initialized = await manager.initialize_server("codex")

    assert initialized is not None
    assert initialized.status is ServerStatus.HEALTHY
    assert initialized.initialized is True
    assert initialized.protocol_version == "2025-11-25"
    assert initialized.last_initialized_at is not None
    assert initialized.capability_snapshot is not None
    assert initialized.capability_snapshot.protocol_version == "2025-11-25"
    assert initialized.capability_snapshot.server_info == {
        "name": "codex",
        "version": "1.0.0",
    }
    assert initialized.capability_snapshot.capabilities == {"tools": {}, "resources": {}}


@pytest.mark.asyncio
async def test_initialize_server_marks_degraded_on_error() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        raise RuntimeError("init failed")

    manager = MCPClientManager(transport=transport)
    manager.register("github", "http://github.local")

    initialized = await manager.initialize_server("github")

    assert initialized is not None
    assert initialized.status is ServerStatus.DEGRADED
    assert initialized.initialized is False
    assert initialized.last_error == "init failed"


@pytest.mark.asyncio
async def test_initialize_server_failure_preserves_last_capability_snapshot() -> None:
    calls = 0

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        nonlocal calls
        method = str(request.get("method", ""))
        if method == "initialize":
            calls += 1
            if calls == 1:
                return {
                    "jsonrpc": "2.0",
                    "id": str(request.get("id", "")),
                    "result": {
                        "protocolVersion": "2025-11-25",
                        "serverInfo": {"name": "github", "version": "2.0.0"},
                        "capabilities": {"tools": {}},
                    },
                }
            raise RuntimeError("init failed")
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("github", "http://github.local")

    first = await manager.initialize_server("github")
    second = await manager.initialize_server("github", force=True)

    assert first is not None
    assert first.capability_snapshot is not None
    assert first.capability_snapshot.server_info == {"name": "github", "version": "2.0.0"}

    assert second is not None
    assert second.initialized is False
    assert second.status is ServerStatus.DEGRADED
    assert second.capability_snapshot is not None
    assert second.capability_snapshot.server_info == {"name": "github", "version": "2.0.0"}


@pytest.mark.asyncio
async def test_initialize_all_returns_all_servers() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"protocolVersion": "2025-11-25"},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("a", "http://a.local")
    manager.register("b", "http://b.local")

    results = await manager.initialize_all()

    assert [server.name for server in results] == ["a", "b"]
    assert all(server.initialized for server in results)


@pytest.mark.asyncio
async def test_invoke_tool_auto_initializes_server_before_tool_call() -> None:
    calls: list[str] = []

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        calls.append(method)
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("codex", "http://codex.local")

    result = await manager.invoke_tool("att.project.list")

    assert result.server == "codex"
    assert calls == ["initialize", "notifications/initialized", "tools/call"]
    server = manager.get("codex")
    assert server is not None
    assert server.initialized is True


@pytest.mark.asyncio
async def test_connect_server_runs_health_and_initialize() -> None:
    probe_calls: list[str] = []
    transport_calls: list[str] = []

    async def probe(server: ExternalServer) -> tuple[bool, str | None]:
        probe_calls.append(server.name)
        return True, None

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        transport_calls.append(method)
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {},
        }

    manager = MCPClientManager(probe=probe, transport=transport)
    manager.register("codex", "http://codex.local")

    connected = await manager.connect_server("codex")

    assert connected is not None
    assert connected.status is ServerStatus.HEALTHY
    assert connected.initialized is True
    assert probe_calls == ["codex"]
    assert transport_calls == ["initialize", "notifications/initialized"]


@pytest.mark.asyncio
async def test_connect_server_skips_initialize_when_unreachable() -> None:
    transport_calls: list[str] = []

    async def probe(server: ExternalServer) -> tuple[bool, str | None]:
        return False, "down"

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        transport_calls.append(str(request.get("method", "")))
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {},
        }

    manager = MCPClientManager(probe=probe, transport=transport, unreachable_after=1)
    manager.register("codex", "http://codex.local")

    connected = await manager.connect_server("codex")

    assert connected is not None
    assert connected.status is ServerStatus.UNREACHABLE
    assert connected.initialized is False
    assert transport_calls == []


class _ModelPayload:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, *, mode: str = "python", exclude_none: bool = False) -> dict[str, Any]:
        del mode, exclude_none
        return self._payload


class _FakeNatSession:
    def __init__(self, *, session_id: str = "session-0") -> None:
        self.session_id = session_id
        self.initialized = False
        self.calls: list[tuple[str, str]] = []
        self.fail_with: Exception | None = None

    async def initialize(self) -> _ModelPayload:
        self.calls.append(("session", "initialize"))
        self.initialized = True
        return _ModelPayload(
            {
                "protocolVersion": "2025-11-25",
                "serverInfo": {"name": "nat"},
                "capabilities": {"tools": {}, "resources": {}},
            }
        )

    async def send_notification(
        self,
        notification: object,
        related_request_id: str | int | None = None,
    ) -> None:
        del notification, related_request_id
        self.calls.append(("session", "notifications/initialized"))

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
        progress_callback: object | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> _ModelPayload:
        del read_timeout_seconds, progress_callback, meta
        self.calls.append(("tool", name))
        if self.fail_with is not None:
            raise self.fail_with
        return _ModelPayload(
            {
                "content": [{"type": "text", "text": "ok"}],
                "structuredContent": {
                    "arguments": arguments or {},
                    "session_id": self.session_id,
                },
                "isError": False,
            }
        )

    async def read_resource(self, uri: object) -> _ModelPayload:
        self.calls.append(("resource", str(uri)))
        return _ModelPayload(
            {
                "contents": [{"uri": str(uri), "mimeType": "text/plain", "text": "data"}],
            }
        )


class _FakeNatSessionFactory:
    def __init__(self) -> None:
        self.created = 0
        self.closed = 0
        self.sessions: list[_FakeNatSession] = []

    @asynccontextmanager
    async def __call__(self, _: str) -> Any:
        session = _FakeNatSession(session_id=f"session-{self.created + 1}")
        self.created += 1
        self.sessions.append(session)
        try:
            yield session
        finally:
            self.closed += 1


@pytest.mark.asyncio
async def test_nat_transport_adapter_initialize_and_invoke_happy_path() -> None:
    session = _FakeNatSession()

    @asynccontextmanager
    async def session_context(_: str) -> Any:
        yield session

    adapter = NATMCPTransportAdapter(session_factory=session_context)
    server = ExternalServer(name="nat", url="http://nat.local")

    initialize = await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {},
        },
    )
    assert isinstance(initialize["result"], dict)
    assert initialize["result"]["protocolVersion"] == "2025-11-25"

    initialized = await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": "init-notify",
            "method": "notifications/initialized",
            "params": {},
        },
    )
    assert initialized["result"] == {}

    tool_call = await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": "tool-1",
            "method": "tools/call",
            "params": {"name": "att.project.list", "arguments": {"limit": 1}},
        },
    )
    assert isinstance(tool_call["result"], dict)
    assert tool_call["result"]["isError"] is False

    resource_read = await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": "resource-1",
            "method": "resources/read",
            "params": {"uri": "att://projects"},
        },
    )
    assert isinstance(resource_read["result"], dict)
    assert resource_read["result"]["contents"][0]["uri"] == "att://projects"
    assert session.calls == [
        ("session", "initialize"),
        ("session", "notifications/initialized"),
        ("tool", "att.project.list"),
        ("resource", "att://projects"),
    ]


@pytest.mark.asyncio
async def test_nat_transport_adapter_session_diagnostics_and_invalidate() -> None:
    session = _FakeNatSession()

    @asynccontextmanager
    async def session_context(_: str) -> Any:
        yield session

    adapter = NATMCPTransportAdapter(session_factory=session_context)
    server = ExternalServer(name="nat", url="http://nat.local")

    before = adapter.session_diagnostics("nat")
    assert before.active is False
    assert before.initialized is False
    assert before.last_activity_at is None

    await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": "tool-1",
            "method": "tools/call",
            "params": {"name": "att.project.list", "arguments": {}},
        },
    )

    after = adapter.session_diagnostics("nat")
    assert after.active is True
    assert after.initialized is True
    assert after.last_activity_at is not None

    invalidated = await adapter.invalidate_session("nat")
    assert invalidated is True

    final = adapter.session_diagnostics("nat")
    assert final.active is False
    assert final.initialized is False
    assert final.last_activity_at is None


@pytest.mark.asyncio
async def test_manager_adapter_session_controls_invalidate_and_refresh() -> None:
    factory = _FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register("nat", "http://nat.local")

    assert manager.supports_adapter_session_controls() is True
    diagnostics = manager.adapter_session_diagnostics("nat")
    assert diagnostics is not None
    assert diagnostics.active is False

    initialized = await manager.initialize_server("nat")
    assert initialized is not None
    assert initialized.initialized is True
    assert factory.created == 1

    after_initialize = manager.adapter_session_diagnostics("nat")
    assert after_initialize is not None
    assert after_initialize.active is True
    assert after_initialize.initialized is True
    assert after_initialize.last_activity_at is not None

    invalidated = await manager.invalidate_adapter_session("nat")
    assert invalidated is True
    assert factory.closed == 1
    server = manager.get("nat")
    assert server is not None
    assert server.initialized is False

    refreshed = await manager.refresh_adapter_session("nat")
    assert refreshed is not None
    assert refreshed.initialized is True
    assert factory.created == 2


@pytest.mark.asyncio
async def test_manager_adapter_session_controls_absent_for_non_nat_adapter() -> None:
    manager = MCPClientManager(transport_adapter=_FakeNatSession())  # type: ignore[arg-type]
    manager.register("nat", "http://nat.local")

    assert manager.supports_adapter_session_controls() is False
    assert manager.adapter_session_diagnostics("nat") is None
    assert await manager.invalidate_adapter_session("nat") is False


@pytest.mark.asyncio
async def test_refresh_adapter_session_recreates_underlying_session_identity() -> None:
    factory = _FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register("nat", "http://nat.local")

    first = await manager.invoke_tool("att.project.list", preferred=["nat"])
    assert isinstance(first.result, dict)
    first_session_id = first.result["structuredContent"]["session_id"]
    assert first_session_id == "session-1"

    refreshed = await manager.refresh_adapter_session("nat")
    assert refreshed is not None
    assert factory.created == 2
    assert factory.closed == 1
    assert factory.sessions[0] is not factory.sessions[1]

    second = await manager.invoke_tool("att.project.list", preferred=["nat"])
    assert isinstance(second.result, dict)
    second_session_id = second.result["structuredContent"]["session_id"]
    assert second_session_id == "session-2"
    assert second_session_id != first_session_id


@pytest.mark.asyncio
async def test_transport_disconnect_invalidation_recreates_session_on_next_invoke() -> None:
    factory = _FakeNatSessionFactory()

    @asynccontextmanager
    async def session_context(endpoint: str) -> Any:
        async with factory(endpoint) as session:
            if session.session_id == "session-1":
                session.fail_with = httpx.ReadTimeout("timed out")
            yield session

    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=session_context),
        max_backoff_seconds=0,
    )
    manager.register("nat", "http://nat.local")

    with pytest.raises(MCPInvocationError):
        await manager.invoke_tool("att.project.list", preferred=["nat"])

    first_diag = manager.adapter_session_diagnostics("nat")
    assert first_diag is not None
    assert first_diag.active is False
    assert factory.created == 1
    assert factory.closed == 1

    retry = await manager.invoke_tool("att.project.list", preferred=["nat"])
    assert retry.server == "nat"
    assert isinstance(retry.result, dict)
    assert retry.result["structuredContent"]["session_id"] == "session-2"
    assert factory.created == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "category"),
    [
        (httpx.ReadTimeout("timed out"), "network_timeout"),
        (
            httpx.HTTPStatusError(
                "bad status",
                request=httpx.Request("POST", "http://nat.local/mcp"),
                response=httpx.Response(
                    503,
                    request=httpx.Request("POST", "http://nat.local/mcp"),
                ),
            ),
            "http_status",
        ),
        (ValueError("bad payload"), "invalid_payload"),
    ],
)
async def test_nat_transport_adapter_category_mapping_parity(
    failure: Exception,
    category: str,
) -> None:
    session = _FakeNatSession()
    session.fail_with = failure

    @asynccontextmanager
    async def session_context(_: str) -> Any:
        yield session

    adapter = NATMCPTransportAdapter(session_factory=session_context)
    server = ExternalServer(name="nat", url="http://nat.local")

    with pytest.raises(MCPTransportError) as exc_info:
        await adapter(
            server,
            {
                "jsonrpc": "2.0",
                "id": "tool-1",
                "method": "tools/call",
                "params": {"name": "att.project.list", "arguments": {}},
            },
        )
    assert exc_info.value.category == category


@pytest.mark.asyncio
async def test_adapter_transport_fallback_across_mixed_states() -> None:
    sessions: dict[str, _FakeNatSession] = {}

    @asynccontextmanager
    async def session_context(endpoint: str) -> Any:
        if "primary.local" in endpoint:
            key = "primary"
        elif "recovered.local" in endpoint:
            key = "recovered"
        else:
            key = "degraded"
        session = sessions.setdefault(key, _FakeNatSession())
        if key == "primary":
            session.fail_with = RuntimeError("primary unavailable")
        yield session

    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=session_context),
        max_initialization_age_seconds=None,
    )
    manager.register("primary", "http://primary.local")
    manager.register("recovered", "http://recovered.local")
    manager.register("degraded", "http://degraded.local")

    primary = manager.get("primary")
    assert primary is not None
    primary.status = ServerStatus.HEALTHY
    primary.initialized = True
    primary.last_initialized_at = datetime.now(UTC)
    primary.initialization_expires_at = datetime.now(UTC) + timedelta(seconds=60)

    recovered = manager.get("recovered")
    assert recovered is not None
    recovered.status = ServerStatus.HEALTHY
    recovered.initialized = False

    manager.record_check_result("degraded", healthy=False, error="down")
    degraded = manager.get("degraded")
    assert degraded is not None
    degraded.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)

    result = await manager.invoke_tool(
        "att.project.list",
        preferred=["primary", "recovered", "degraded"],
    )

    assert result.server == "recovered"
    assert sessions["primary"].calls == [
        ("session", "initialize"),
        ("tool", "att.project.list"),
    ]
    assert sessions["recovered"].calls == [
        ("session", "initialize"),
        ("session", "notifications/initialized"),
        ("tool", "att.project.list"),
    ]
    assert "degraded" not in sessions


@pytest.mark.asyncio
async def test_invocation_failure_records_correlation_id_on_connection_events() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if method == "initialize":
            raise RuntimeError("init down")
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("codex", "http://codex.local")

    with pytest.raises(MCPInvocationError):
        await manager.invoke_tool("att.project.list")

    invocation_events = manager.list_invocation_events()
    assert invocation_events
    request_id = invocation_events[0].request_id

    correlated_events = manager.list_events(correlation_id=request_id)
    assert len(correlated_events) == 1
    assert correlated_events[0].server == "codex"
    assert correlated_events[0].correlation_id == request_id


@pytest.mark.asyncio
async def test_event_list_filters_and_limits() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if server.name == "primary":
            raise RuntimeError("primary unavailable")
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")

    result = await manager.invoke_tool("att.project.list", preferred=["primary", "backup"])
    request_id = result.request_id
    manager.record_check_result("backup", healthy=False, error="manual degrade")

    primary_invocation = manager.list_invocation_events(server="primary", request_id=request_id)
    assert [event.phase for event in primary_invocation] == [
        "initialize_start",
        "initialize_failure",
    ]

    latest_invocation = manager.list_invocation_events(limit=2)
    assert [event.phase for event in latest_invocation] == [
        "invoke_start",
        "invoke_success",
    ]

    correlated_connection = manager.list_events(correlation_id=request_id)
    assert len(correlated_connection) == 1
    assert correlated_connection[0].server == "primary"

    backup_connection = manager.list_events(server="backup")
    assert len(backup_connection) == 1
    assert backup_connection[0].correlation_id is None

    latest_connection = manager.list_events(limit=1)
    assert len(latest_connection) == 1
    assert latest_connection[0].server == "backup"
