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
from tests.support.mcp_helpers import MCPTestClock
from tests.support.mcp_nat_helpers import (
    ClusterNatSessionFactory,
    FakeNatSession,
    FakeNatSessionFactory,
)

UNIT_TEST_TIMEOUT_ERROR_CATEGORY = "network_timeout"
UNIT_TEST_TRANSPORT_ERROR_CATEGORY = "transport_error"
UNIT_TEST_RPC_ERROR_CATEGORY = "rpc_error"
UNIT_TEST_HTTP_STATUS_ERROR_CATEGORY = "http_status"
UNIT_TEST_INITIALIZE_METHOD = "initialize"
UNIT_TEST_TOOLS_CALL_METHOD = "tools/call"
UNIT_TEST_RESOURCES_READ_METHOD = "resources/read"
UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD = "notifications/initialized"
UNIT_TEST_PRIMARY_SERVER = "primary"
UNIT_TEST_BACKUP_SERVER = "backup"
UNIT_TEST_SECONDARY_SERVER = "secondary"
UNIT_TEST_RECOVERED_SERVER = "recovered"
UNIT_TEST_DEGRADED_SERVER = "degraded"
UNIT_TEST_NAT_SERVER = "nat"
UNIT_TEST_SERVER_A = "a"
UNIT_TEST_SERVER_B = "b"
UNIT_TEST_SERVER_C = "c"
UNIT_TEST_CODEX_SERVER = "codex"
UNIT_TEST_INITIALIZE_START_PHASE = "initialize_start"
UNIT_TEST_INITIALIZE_FAILURE_PHASE = "initialize_failure"
UNIT_TEST_INITIALIZE_SUCCESS_PHASE = "initialize_success"
UNIT_TEST_INVOKE_STAGE = "invoke"
UNIT_TEST_INVOKE_START_PHASE = "invoke_start"
UNIT_TEST_INVOKE_FAILURE_PHASE = "invoke_failure"
UNIT_TEST_INVOKE_SUCCESS_PHASE = "invoke_success"
UNIT_TEST_SESSION_ID_FIRST = "session-1"
UNIT_TEST_SESSION_ID_SECOND = "session-2"
UNIT_TEST_PROTOCOL_VERSION = "2025-11-25"
UNIT_TEST_PROJECTS_URI = "att://projects"
UNIT_TEST_FRESHNESS_UNKNOWN = "unknown"
UNIT_TEST_FRESHNESS_ACTIVE_RECENT = "active_recent"
UNIT_TEST_FRESHNESS_STALE = "stale"
UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR = ("ok",)
UNIT_TEST_FAILURE_SCRIPT_ERROR_VECTOR = ("error",)
UNIT_TEST_FAILURE_ACTION_ERROR = "error"
UNIT_TEST_FAILURE_ACTION_OK = "ok"
UNIT_TEST_FAILURE_ACTION_TIMEOUT = "timeout"


@pytest.mark.asyncio
async def test_health_check_probe_updates_status_and_logs_transition() -> None:
    async def flaky_probe(_: object) -> tuple[bool, str | None]:
        return False, "timeout"

    clock = MCPTestClock()
    manager = MCPClientManager(
        probe=flaky_probe,
        unreachable_after=2,
        now_provider=clock,
    )
    manager.register("codex", "http://codex.local")

    await manager.health_check_server("codex")
    server = manager.get("codex")
    assert server is not None
    assert server.status is ServerStatus.DEGRADED
    assert server.retry_count == 1
    assert server.last_error == "timeout"
    clock.advance(seconds=1)

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


@pytest.mark.asyncio
async def test_should_retry_uses_injected_clock_when_now_omitted() -> None:
    clock = MCPTestClock()
    manager = MCPClientManager(now_provider=clock)
    manager.register("terminal", "http://terminal.local")
    manager.record_check_result("terminal", healthy=False, error="down")

    assert manager.should_retry("terminal") is False
    clock.advance(seconds=1)
    assert manager.should_retry("terminal") is True


def test_choose_server_prefers_healthy_then_degraded() -> None:
    manager = MCPClientManager()
    manager.register("a", "http://a.local")
    manager.register("b", "http://b.local")

    manager.record_check_result("a", healthy=False, error="slow")

    selected = manager.choose_server()
    assert selected is not None
    assert selected.name == UNIT_TEST_SERVER_B

    manager.record_check_result("b", healthy=False, error="down")
    fallback = manager.choose_server(preferred=["a", "b"])
    assert fallback is not None
    assert fallback.name == UNIT_TEST_SERVER_A


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
    assert result.server == UNIT_TEST_BACKUP_SERVER
    assert result.method == UNIT_TEST_TOOLS_CALL_METHOD
    assert isinstance(result.result, dict)
    assert result.result["ok"] is True
    assert calls[0] == (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
    assert calls[-1] == (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)

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
    assert result.server == UNIT_TEST_SECONDARY_SERVER
    assert result.method == UNIT_TEST_RESOURCES_READ_METHOD
    assert isinstance(result.result, dict)
    assert result.result["uri"] == UNIT_TEST_PROJECTS_URI
    assert calls[0] == (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
    assert calls[-1] == (UNIT_TEST_SECONDARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD)


@pytest.mark.asyncio
async def test_invoke_tool_raises_when_no_servers_available() -> None:
    manager = MCPClientManager()
    with pytest.raises(MCPInvocationError) as exc_info:
        await manager.invoke_tool("att.project.list")
    assert exc_info.value.method == UNIT_TEST_TOOLS_CALL_METHOD
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
    assert error.method == UNIT_TEST_TOOLS_CALL_METHOD
    assert len(error.attempts) == 3
    assert error.attempts[0].server == UNIT_TEST_PRIMARY_SERVER
    assert error.attempts[0].stage == UNIT_TEST_INITIALIZE_METHOD
    assert error.attempts[0].success is False
    assert error.attempts[0].error == "primary down"
    assert error.attempts[0].error_category == UNIT_TEST_TRANSPORT_ERROR_CATEGORY
    assert error.attempts[1].server == UNIT_TEST_BACKUP_SERVER
    assert error.attempts[1].stage == UNIT_TEST_INITIALIZE_METHOD
    assert error.attempts[1].success is True
    assert error.attempts[1].error_category is None
    assert error.attempts[2].server == UNIT_TEST_BACKUP_SERVER
    assert error.attempts[2].stage == UNIT_TEST_INVOKE_STAGE
    assert error.attempts[2].success is False
    assert error.attempts[2].error == "rpc error: rpc failure"
    assert error.attempts[2].error_category == UNIT_TEST_RPC_ERROR_CATEGORY


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

    assert result.server == UNIT_TEST_CODEX_SERVER
    assert calls == [
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD,
        UNIT_TEST_TOOLS_CALL_METHOD,
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
    assert error.attempts[1].stage == UNIT_TEST_INVOKE_STAGE
    assert error.attempts[1].error_category == UNIT_TEST_HTTP_STATUS_ERROR_CATEGORY
    server = manager.get("codex")
    assert server is not None
    assert server.last_error_category == UNIT_TEST_HTTP_STATUS_ERROR_CATEGORY


@pytest.mark.asyncio
async def test_invoke_tool_mixed_state_cluster_recovers_in_preferred_order() -> None:
    calls: list[tuple[str, str]] = []
    clock = MCPTestClock()

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

    manager = MCPClientManager(
        transport=transport,
        max_initialization_age_seconds=None,
        now_provider=clock,
    )
    manager.register("primary", "http://primary.local")
    manager.register("recovered", "http://recovered.local")
    manager.register("degraded", "http://degraded.local")

    primary = manager.get("primary")
    assert primary is not None
    primary.status = ServerStatus.HEALTHY
    primary.initialized = True
    primary.last_initialized_at = clock.current
    primary.initialization_expires_at = clock.current + timedelta(seconds=60)

    recovered = manager.get("recovered")
    assert recovered is not None
    recovered.status = ServerStatus.HEALTHY
    recovered.initialized = False

    manager.record_check_result("degraded", healthy=False, error="down")
    clock.advance(seconds=2)

    result = await manager.invoke_tool(
        "att.project.list",
        preferred=["primary", "recovered", "degraded"],
    )

    assert result.server == UNIT_TEST_RECOVERED_SERVER
    assert calls[0] == (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)
    assert calls[1] == (UNIT_TEST_RECOVERED_SERVER, UNIT_TEST_INITIALIZE_METHOD)
    assert calls[2] == (
        UNIT_TEST_RECOVERED_SERVER,
        UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD,
    )
    assert calls[3] == (UNIT_TEST_RECOVERED_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)
    assert (UNIT_TEST_DEGRADED_SERVER, UNIT_TEST_INITIALIZE_METHOD) not in calls
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
    assert result.server == UNIT_TEST_BACKUP_SERVER

    events = manager.list_invocation_events()
    phases = [event.phase for event in events]
    assert phases == [
        UNIT_TEST_INITIALIZE_START_PHASE,
        UNIT_TEST_INITIALIZE_FAILURE_PHASE,
        UNIT_TEST_INITIALIZE_START_PHASE,
        UNIT_TEST_INITIALIZE_SUCCESS_PHASE,
        UNIT_TEST_INVOKE_START_PHASE,
        UNIT_TEST_INVOKE_SUCCESS_PHASE,
    ]
    servers = [event.server for event in events]
    assert servers == [
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_BACKUP_SERVER,
    ]
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
        UNIT_TEST_INITIALIZE_SUCCESS_PHASE,
        UNIT_TEST_INVOKE_START_PHASE,
        UNIT_TEST_INVOKE_SUCCESS_PHASE,
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
    assert initialized.protocol_version == UNIT_TEST_PROTOCOL_VERSION
    assert initialized.last_initialized_at is not None
    assert initialized.capability_snapshot is not None
    assert initialized.capability_snapshot.protocol_version == UNIT_TEST_PROTOCOL_VERSION
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

    assert [server.name for server in results] == [UNIT_TEST_SERVER_A, UNIT_TEST_SERVER_B]
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

    assert result.server == UNIT_TEST_CODEX_SERVER
    assert calls == [
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD,
        UNIT_TEST_TOOLS_CALL_METHOD,
    ]
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
    assert probe_calls == [UNIT_TEST_CODEX_SERVER]
    assert transport_calls == [
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD,
    ]


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


@pytest.mark.asyncio
async def test_nat_transport_adapter_initialize_and_invoke_happy_path() -> None:
    session = FakeNatSession()

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
    assert initialize["result"]["protocolVersion"] == UNIT_TEST_PROTOCOL_VERSION

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
    assert resource_read["result"]["contents"][0]["uri"] == UNIT_TEST_PROJECTS_URI
    assert session.calls == [
        ("session", UNIT_TEST_INITIALIZE_METHOD),
        ("session", UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD),
        ("tool", "att.project.list"),
        ("resource", UNIT_TEST_PROJECTS_URI),
    ]


@pytest.mark.asyncio
async def test_nat_transport_adapter_session_diagnostics_and_invalidate() -> None:
    session = FakeNatSession()

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
    factory = FakeNatSessionFactory()
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
    manager = MCPClientManager(transport_adapter=FakeNatSession())  # type: ignore[arg-type]
    manager.register("nat", "http://nat.local")

    assert manager.supports_adapter_session_controls() is False
    assert manager.adapter_session_diagnostics(UNIT_TEST_NAT_SERVER) is None
    assert await manager.invalidate_adapter_session(UNIT_TEST_NAT_SERVER) is False
    assert manager.list_adapter_sessions() == []


@pytest.mark.asyncio
async def test_manager_list_adapter_sessions_returns_sorted_aggregate() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register("b", "http://b.local")
    manager.register("a", "http://a.local")

    before = manager.list_adapter_sessions()
    assert [item.server for item in before] == [UNIT_TEST_SERVER_A, UNIT_TEST_SERVER_B]
    assert all(item.active is False for item in before)

    await manager.invoke_tool("att.project.list", preferred=["b"])

    after = manager.list_adapter_sessions()
    by_name = {item.server: item for item in after}
    assert by_name[UNIT_TEST_SERVER_B].active is True
    assert by_name[UNIT_TEST_SERVER_B].initialized is True
    assert by_name[UNIT_TEST_SERVER_B].last_activity_at is not None
    assert by_name[UNIT_TEST_SERVER_A].active is False


@pytest.mark.asyncio
async def test_manager_list_adapter_sessions_supports_filters_and_limit() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register("a", "http://a.local")
    manager.register("b", "http://b.local")
    manager.register("c", "http://c.local")

    await manager.invoke_tool("att.project.list", preferred=["a"])
    await manager.invoke_tool("att.project.list", preferred=["c"])

    active_only = manager.list_adapter_sessions(active_only=True)
    assert [item.server for item in active_only] == [UNIT_TEST_SERVER_A, UNIT_TEST_SERVER_C]

    only_c = manager.list_adapter_sessions(server_name="c")
    assert [item.server for item in only_c] == [UNIT_TEST_SERVER_C]
    assert only_c[0].active is True

    limited = manager.list_adapter_sessions(limit=1)
    assert [item.server for item in limited] == [UNIT_TEST_SERVER_C]


@pytest.mark.asyncio
async def test_manager_adapter_session_freshness_semantics() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        adapter_session_stale_after_seconds=300,
    )
    manager.register("nat", "http://nat.local")

    initial = manager.adapter_session_diagnostics("nat")
    assert initial is not None
    assert initial.freshness == UNIT_TEST_FRESHNESS_UNKNOWN

    await manager.invoke_tool("att.project.list", preferred=["nat"])

    recent = manager.adapter_session_diagnostics("nat")
    assert recent is not None
    assert recent.active is True
    assert recent.freshness == UNIT_TEST_FRESHNESS_ACTIVE_RECENT

    adapter = manager._adapter_with_session_controls()
    assert adapter is not None
    adapter._sessions["nat"].last_activity_at = datetime.now(UTC) - timedelta(seconds=301)

    stale = manager.adapter_session_diagnostics("nat")
    assert stale is not None
    assert stale.freshness == UNIT_TEST_FRESHNESS_STALE

    listing = manager.list_adapter_sessions(server_name="nat")
    assert len(listing) == 1
    assert listing[0].freshness == UNIT_TEST_FRESHNESS_STALE


@pytest.mark.asyncio
async def test_manager_list_adapter_sessions_supports_freshness_filter() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        adapter_session_stale_after_seconds=60,
    )
    manager.register("a", "http://a.local")
    manager.register("b", "http://b.local")

    await manager.invoke_tool("att.project.list", preferred=["a"])

    adapter = manager._adapter_with_session_controls()
    assert adapter is not None
    adapter._sessions["a"].last_activity_at = datetime.now(UTC) - timedelta(seconds=61)

    stale = manager.list_adapter_sessions(freshness="stale")
    assert [item.server for item in stale] == [UNIT_TEST_SERVER_A]

    unknown = manager.list_adapter_sessions(freshness="unknown")
    assert [item.server for item in unknown] == [UNIT_TEST_SERVER_B]

    recent = manager.list_adapter_sessions(freshness="active_recent")
    assert recent == []


@pytest.mark.asyncio
async def test_refresh_adapter_session_recreates_underlying_session_identity() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register("nat", "http://nat.local")

    first = await manager.invoke_tool("att.project.list", preferred=["nat"])
    assert isinstance(first.result, dict)
    first_session_id = first.result["structuredContent"]["session_id"]
    assert first_session_id == UNIT_TEST_SESSION_ID_FIRST

    refreshed = await manager.refresh_adapter_session("nat")
    assert refreshed is not None
    assert factory.created == 2
    assert factory.closed == 1
    assert factory.sessions[0] is not factory.sessions[1]

    second = await manager.invoke_tool("att.project.list", preferred=["nat"])
    assert isinstance(second.result, dict)
    second_session_id = second.result["structuredContent"]["session_id"]
    assert second_session_id == UNIT_TEST_SESSION_ID_SECOND
    assert second_session_id != first_session_id


@pytest.mark.asyncio
async def test_transport_disconnect_invalidation_recreates_session_on_next_invoke() -> None:
    factory = FakeNatSessionFactory()

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
    assert retry.server == UNIT_TEST_NAT_SERVER
    assert isinstance(retry.result, dict)
    assert retry.result["structuredContent"]["session_id"] == UNIT_TEST_SESSION_ID_SECOND
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
    session = FakeNatSession()
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
    sessions: dict[str, FakeNatSession] = {}
    clock = MCPTestClock()

    @asynccontextmanager
    async def session_context(endpoint: str) -> Any:
        if "primary.local" in endpoint:
            key = "primary"
        elif "recovered.local" in endpoint:
            key = "recovered"
        else:
            key = "degraded"
        session = sessions.setdefault(key, FakeNatSession())
        if key == "primary":
            session.fail_with = RuntimeError("primary unavailable")
        yield session

    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=session_context),
        max_initialization_age_seconds=None,
        now_provider=clock,
    )
    manager.register("primary", "http://primary.local")
    manager.register("recovered", "http://recovered.local")
    manager.register("degraded", "http://degraded.local")

    primary = manager.get("primary")
    assert primary is not None
    primary.status = ServerStatus.HEALTHY
    primary.initialized = True
    primary.last_initialized_at = clock.current
    primary.initialization_expires_at = clock.current + timedelta(seconds=60)

    recovered = manager.get("recovered")
    assert recovered is not None
    recovered.status = ServerStatus.HEALTHY
    recovered.initialized = False

    manager.record_check_result("degraded", healthy=False, error="down")
    clock.advance(seconds=2)

    result = await manager.invoke_tool(
        "att.project.list",
        preferred=["primary", "recovered", "degraded"],
    )

    assert result.server == UNIT_TEST_RECOVERED_SERVER
    assert sessions[UNIT_TEST_PRIMARY_SERVER].calls == [
        ("session", UNIT_TEST_INITIALIZE_METHOD),
        ("tool", "att.project.list"),
    ]
    assert sessions[UNIT_TEST_RECOVERED_SERVER].calls == [
        ("session", UNIT_TEST_INITIALIZE_METHOD),
        ("session", UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD),
        ("tool", "att.project.list"),
    ]
    assert UNIT_TEST_DEGRADED_SERVER not in sessions


def test_cluster_nat_failure_script_order_and_validation() -> None:
    factory = ClusterNatSessionFactory()

    factory.set_failure_script("primary", "initialize", ["ok", "timeout", "error"])
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
        == UNIT_TEST_FAILURE_ACTION_OK
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
        == UNIT_TEST_FAILURE_ACTION_TIMEOUT
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
        == UNIT_TEST_FAILURE_ACTION_ERROR
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
        is None
    )

    factory.set_failure_script("primary", "tools/call", ["ok"])
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)
        == UNIT_TEST_FAILURE_ACTION_OK
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)
        is None
    )

    factory.set_failure_script("primary", "resources/read", ["ok"])
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD)
        == UNIT_TEST_FAILURE_ACTION_OK
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD)
        is None
    )

    factory.set_failure_script("primary", "initialize", ["invalid"])
    with pytest.raises(ValueError, match="unsupported scripted action"):
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)


def test_cluster_nat_failure_script_isolation_across_servers_and_methods() -> None:
    factory = ClusterNatSessionFactory()

    factory.set_failure_script("primary", "initialize", ["timeout", "ok"])
    factory.set_failure_script("primary", "resources/read", ["error"])
    factory.set_failure_script("backup", "initialize", ["ok"])
    factory.set_failure_script("backup", "tools/call", ["error", "ok"])

    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
        == UNIT_TEST_FAILURE_ACTION_TIMEOUT
    )
    assert factory.failure_scripts[(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)] == list(
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR
    )
    assert factory.failure_scripts[
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD)
    ] == list(UNIT_TEST_FAILURE_SCRIPT_ERROR_VECTOR)
    assert factory.failure_scripts[(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_INITIALIZE_METHOD)] == list(
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR
    )
    assert factory.failure_scripts[(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)] == [
        "error",
        "ok",
    ]

    assert (
        factory.consume_failure_action(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)
        == UNIT_TEST_FAILURE_ACTION_ERROR
    )
    assert factory.failure_scripts[(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)] == list(
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR
    )
    assert factory.failure_scripts[
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD)
    ] == list(UNIT_TEST_FAILURE_SCRIPT_ERROR_VECTOR)
    assert factory.failure_scripts[(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_INITIALIZE_METHOD)] == list(
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR
    )
    assert factory.failure_scripts[(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)] == list(
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR
    )

    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD)
        == UNIT_TEST_FAILURE_ACTION_ERROR
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_INITIALIZE_METHOD)
        == UNIT_TEST_FAILURE_ACTION_OK
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
        == UNIT_TEST_FAILURE_ACTION_OK
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)
        == UNIT_TEST_FAILURE_ACTION_OK
    )

    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
        is None
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD)
        is None
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_INITIALIZE_METHOD) is None
    )
    assert (
        factory.consume_failure_action(UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD) is None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_key", "expected_method"),
    [
        ("initialize", "tools/call"),
        ("tools/call", "tools/call"),
        ("resources/read", "resources/read"),
    ],
)
async def test_cluster_nat_failure_script_exhaustion_falls_back_to_set_toggles(
    method_key: str,
    expected_method: str,
) -> None:
    clock = MCPTestClock()
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
    )
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")

    if method_key == "initialize":
        factory.fail_on_timeout_initialize.add("primary")
        factory.set_failure_script("primary", "initialize", ["ok"])
    elif method_key == "tools/call":
        factory.fail_on_timeout_tool_calls.add("primary")
        factory.set_failure_script("primary", "tools/call", ["ok"])
    else:
        factory.fail_on_timeout_resource_reads.add("primary")
        factory.set_failure_script("primary", "resources/read", ["ok"])

    if method_key == "resources/read":
        first = await manager.read_resource("att://projects", preferred=["primary", "backup"])
    else:
        first = await manager.invoke_tool("att.project.list", preferred=["primary", "backup"])
    assert first.server == UNIT_TEST_PRIMARY_SERVER

    if method_key == "initialize":
        invalidated = await manager.invalidate_adapter_session("primary")
        assert invalidated is True

    if method_key == "resources/read":
        second = await manager.read_resource("att://projects", preferred=["primary", "backup"])
    else:
        second = await manager.invoke_tool("att.project.list", preferred=["primary", "backup"])
    assert second.server == UNIT_TEST_BACKUP_SERVER
    assert second.method == expected_method

    primary_events = manager.list_invocation_events(
        server="primary",
        method=expected_method,
        request_id=second.request_id,
    )
    if method_key == "initialize":
        assert [event.phase for event in primary_events] == [
            UNIT_TEST_INITIALIZE_START_PHASE,
            UNIT_TEST_INITIALIZE_FAILURE_PHASE,
        ]
        assert primary_events[1].error_category == UNIT_TEST_TIMEOUT_ERROR_CATEGORY
    else:
        assert [event.phase for event in primary_events] == [
            UNIT_TEST_INITIALIZE_START_PHASE,
            UNIT_TEST_INITIALIZE_SUCCESS_PHASE,
            UNIT_TEST_INVOKE_START_PHASE,
            UNIT_TEST_INVOKE_FAILURE_PHASE,
        ]
        assert primary_events[3].error_category == UNIT_TEST_TIMEOUT_ERROR_CATEGORY

    primary = manager.get("primary")
    assert primary is not None
    assert primary.status is ServerStatus.DEGRADED
    assert primary.last_error_category == UNIT_TEST_TIMEOUT_ERROR_CATEGORY


@pytest.mark.asyncio
async def test_cluster_nat_call_order_is_stable_for_mixed_scripted_failover() -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
    )
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")

    factory.set_failure_script("primary", "tools/call", ["timeout"])
    factory.set_failure_script("backup", "resources/read", ["timeout"])

    first = await manager.invoke_tool(
        "att.project.list",
        preferred=["primary", "backup"],
    )
    assert first.server == UNIT_TEST_BACKUP_SERVER
    clock.advance(seconds=1)

    second = await manager.read_resource(
        "att://projects",
        preferred=["backup", "primary"],
    )
    assert second.server == UNIT_TEST_PRIMARY_SERVER

    call_order = [
        (server, method)
        for server, _, method in factory.calls
        if method
        in {
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_TOOLS_CALL_METHOD,
            UNIT_TEST_RESOURCES_READ_METHOD,
        }
    ]
    assert call_order == [
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_TOOLS_CALL_METHOD),
        (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD),
        (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_RESOURCES_READ_METHOD),
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["tools/call", "resources/read"])
async def test_cluster_nat_repeated_invokes_skip_initialize_until_invalidate(
    method: str,
) -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register("primary", "http://primary.local")

    async def invoke_once() -> object:
        if method == "resources/read":
            return await manager.read_resource("att://projects", preferred=["primary"])
        return await manager.invoke_tool("att.project.list", preferred=["primary"])

    first = await invoke_once()
    second = await invoke_once()
    assert first.server == UNIT_TEST_PRIMARY_SERVER
    assert second.server == UNIT_TEST_PRIMARY_SERVER
    assert first.method == method
    assert second.method == method

    before_invalidate = [
        (server, session_id, call_method)
        for server, session_id, call_method in factory.calls
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]
    assert [call_method for _, _, call_method in before_invalidate] == [
        UNIT_TEST_INITIALIZE_METHOD,
        method,
        method,
    ]
    assert before_invalidate[0][0] == UNIT_TEST_PRIMARY_SERVER
    assert before_invalidate[1][1] == before_invalidate[2][1]

    invalidated = await manager.invalidate_adapter_session("primary")
    assert invalidated is True

    third = await invoke_once()
    assert third.server == UNIT_TEST_PRIMARY_SERVER
    assert third.method == method

    call_order = [
        (server, session_id, call_method)
        for server, session_id, call_method in factory.calls
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]
    assert [call_method for _, _, call_method in call_order] == [
        UNIT_TEST_INITIALIZE_METHOD,
        method,
        method,
        UNIT_TEST_INITIALIZE_METHOD,
        method,
    ]
    assert call_order[3][1] != call_order[2][1]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["tools/call", "resources/read"])
@pytest.mark.parametrize("trigger", ["stale_expiry", "degraded_status"])
async def test_cluster_nat_force_reinitialize_triggers_call_order_parity(
    method: str,
    trigger: str,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
    )
    manager.register("primary", "http://primary.local")

    async def invoke_once() -> object:
        if method == "resources/read":
            return await manager.read_resource("att://projects", preferred=["primary"])
        return await manager.invoke_tool("att.project.list", preferred=["primary"])

    first = await invoke_once()
    assert first.server == UNIT_TEST_PRIMARY_SERVER
    assert first.method == method

    primary = manager.get("primary")
    assert primary is not None
    assert primary.initialized is True
    if trigger == "stale_expiry":
        primary.initialization_expires_at = clock.current - timedelta(seconds=1)
    else:
        primary.status = ServerStatus.DEGRADED
        primary.next_retry_at = None

    second = await invoke_once()
    assert second.server == UNIT_TEST_PRIMARY_SERVER
    assert second.method == method

    call_order = [
        (server, call_method)
        for server, _, call_method in factory.calls
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]
    assert call_order == [
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_PRIMARY_SERVER, method),
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_PRIMARY_SERVER, method),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["tools/call", "resources/read"])
@pytest.mark.parametrize(
    ("unreachable_after", "expected_status"),
    [
        (3, ServerStatus.DEGRADED),
        (1, ServerStatus.UNREACHABLE),
    ],
)
async def test_cluster_nat_retry_window_gating_skips_then_reenters_primary_call_order(
    method: str,
    unreachable_after: int,
    expected_status: ServerStatus,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=unreachable_after,
    )
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")
    factory.set_failure_script("primary", method, ["timeout", "ok"])

    async def invoke_once() -> object:
        if method == "resources/read":
            return await manager.read_resource(
                "att://projects",
                preferred=["primary", "backup"],
            )
        return await manager.invoke_tool(
            "att.project.list",
            preferred=["primary", "backup"],
        )

    first = await invoke_once()
    assert first.server == UNIT_TEST_BACKUP_SERVER

    primary = manager.get("primary")
    assert primary is not None
    assert primary.status is expected_status

    calls_after_first = len(factory.calls)
    second = await invoke_once()
    assert second.server == UNIT_TEST_BACKUP_SERVER

    second_slice = factory.calls[calls_after_first:]
    assert second_slice
    assert all(server == UNIT_TEST_BACKUP_SERVER for server, _, _ in second_slice)

    clock.advance(seconds=1)
    manager.record_check_result("backup", healthy=False, error="hold backup")

    calls_before_third = len(factory.calls)
    third = await invoke_once()
    assert third.server == UNIT_TEST_PRIMARY_SERVER
    assert third.method == method

    third_slice = [
        (server, call_method)
        for server, _, call_method in factory.calls[calls_before_third:]
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]
    assert third_slice == [
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_PRIMARY_SERVER, method),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("backup_failures", "expected_backup_status"),
    [
        (1, ServerStatus.DEGRADED),
        (2, ServerStatus.UNREACHABLE),
    ],
)
async def test_cluster_nat_resource_retry_reentry_skips_non_retryable_backup_state(
    backup_failures: int,
    expected_backup_status: ServerStatus,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=2,
    )
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")
    factory.set_failure_script("primary", "resources/read", ["timeout", "ok"])

    first = await manager.read_resource(
        "att://projects",
        preferred=["primary", "backup"],
    )
    assert first.server == UNIT_TEST_BACKUP_SERVER

    second = await manager.read_resource(
        "att://projects",
        preferred=["backup", "primary"],
    )
    assert second.server == UNIT_TEST_BACKUP_SERVER

    clock.advance(seconds=1)
    for _ in range(backup_failures):
        manager.record_check_result("backup", healthy=False, error="hold backup")
    backup = manager.get("backup")
    assert backup is not None
    assert backup.status is expected_backup_status

    calls_before_third = len(factory.calls)
    third = await manager.read_resource(
        "att://projects",
        preferred=["backup", "primary"],
    )
    assert third.server == UNIT_TEST_PRIMARY_SERVER

    third_slice = [
        (server, method)
        for server, _, method in factory.calls[calls_before_third:]
        if method in {UNIT_TEST_INITIALIZE_METHOD, UNIT_TEST_RESOURCES_READ_METHOD}
    ]
    assert third_slice == [
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["tools/call", "resources/read"])
@pytest.mark.parametrize(
    ("primary_failures", "expected_primary_status"),
    [
        (1, ServerStatus.DEGRADED),
        (2, ServerStatus.UNREACHABLE),
    ],
)
async def test_cluster_nat_retry_window_matrix_handles_degraded_and_unreachable_primary(
    method: str,
    primary_failures: int,
    expected_primary_status: ServerStatus,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=2,
    )
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")
    factory.set_failure_script("primary", "initialize", ["timeout"] * primary_failures + ["ok"])

    async def invoke_once(preferred: list[str]) -> object:
        if method == "resources/read":
            return await manager.read_resource("att://projects", preferred=preferred)
        return await manager.invoke_tool("att.project.list", preferred=preferred)

    first = await invoke_once(["primary", "backup"])
    assert first.server == UNIT_TEST_BACKUP_SERVER

    calls_after_first = len(factory.calls)
    second = await invoke_once(["primary", "backup"])
    assert second.server == UNIT_TEST_BACKUP_SERVER
    second_slice = factory.calls[calls_after_first:]
    assert second_slice
    assert all(server == UNIT_TEST_BACKUP_SERVER for server, _, _ in second_slice)

    if primary_failures == 2:
        clock.advance(seconds=1)
        manager.record_check_result("backup", healthy=False, error="hold backup")
        with pytest.raises(MCPInvocationError):
            await invoke_once(["primary"])
        primary = manager.get("primary")
        assert primary is not None
        assert primary.status is ServerStatus.UNREACHABLE

        clock.advance(seconds=1)
        calls_before_fourth = len(factory.calls)
        fourth = await invoke_once(["primary", "backup"])
        assert fourth.server == UNIT_TEST_BACKUP_SERVER
        fourth_slice = factory.calls[calls_before_fourth:]
        assert fourth_slice
        assert all(server == UNIT_TEST_BACKUP_SERVER for server, _, _ in fourth_slice)
        clock.advance(seconds=2)
    else:
        clock.advance(seconds=1)

    primary = manager.get("primary")
    assert primary is not None
    assert primary.status is expected_primary_status

    manager.record_check_result("backup", healthy=False, error="hold backup")

    calls_before_reentry = len(factory.calls)
    reentry = await invoke_once(["backup", "primary"])
    assert reentry.server == UNIT_TEST_PRIMARY_SERVER
    assert reentry.method == method

    reentry_slice = [
        (server, call_method)
        for server, _, call_method in factory.calls[calls_before_reentry:]
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]
    assert reentry_slice == [
        (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_PRIMARY_SERVER, method),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["tools/call", "resources/read"])
async def test_cluster_nat_unreachable_primary_reinitializes_degraded_backup_before_invoke(
    method: str,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=2,
    )
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")
    factory.set_failure_script("primary", "initialize", ["timeout", "timeout", "ok"])

    async def invoke_once(preferred: list[str]) -> object:
        if method == "resources/read":
            return await manager.read_resource("att://projects", preferred=preferred)
        return await manager.invoke_tool("att.project.list", preferred=preferred)

    first = await invoke_once(["primary", "backup"])
    assert first.server == UNIT_TEST_BACKUP_SERVER

    clock.advance(seconds=1)
    manager.record_check_result("backup", healthy=False, error="hold backup")
    with pytest.raises(MCPInvocationError):
        await invoke_once(["primary"])

    primary = manager.get("primary")
    assert primary is not None
    assert primary.status is ServerStatus.UNREACHABLE

    clock.advance(seconds=1)
    calls_before_backup_reentry = len(factory.calls)
    backup_reentry = await invoke_once(["primary", "backup"])
    assert backup_reentry.server == UNIT_TEST_BACKUP_SERVER
    assert backup_reentry.method == method

    backup_reentry_slice = [
        (server, call_method)
        for server, _, call_method in factory.calls[calls_before_backup_reentry:]
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]
    assert backup_reentry_slice == [
        (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_BACKUP_SERVER, method),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("backup_failures", "reopen_seconds", "expected_backup_status"),
    [
        (1, 1, ServerStatus.DEGRADED),
        (2, 2, ServerStatus.UNREACHABLE),
    ],
)
@pytest.mark.parametrize("method", ["tools/call", "resources/read"])
async def test_cluster_nat_unreachable_primary_with_closed_backup_windows_no_candidate_then_reentry(
    backup_failures: int,
    reopen_seconds: int,
    expected_backup_status: ServerStatus,
    method: str,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=2,
    )
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")
    factory.set_failure_script("primary", "initialize", ["timeout", "timeout", "ok"])

    async def invoke_once(preferred: list[str]) -> object:
        if method == "resources/read":
            return await manager.read_resource("att://projects", preferred=preferred)
        return await manager.invoke_tool("att.project.list", preferred=preferred)

    first = await invoke_once(["primary", "backup"])
    assert first.server == UNIT_TEST_BACKUP_SERVER

    clock.advance(seconds=1)
    for _ in range(backup_failures):
        manager.record_check_result("backup", healthy=False, error="hold backup")
    backup = manager.get("backup")
    assert backup is not None
    assert backup.status is expected_backup_status

    with pytest.raises(MCPInvocationError):
        await invoke_once(["primary"])
    primary = manager.get("primary")
    assert primary is not None
    assert primary.status is ServerStatus.UNREACHABLE

    calls_before_no_candidate = len(factory.calls)
    with pytest.raises(MCPInvocationError):
        await invoke_once(["primary", "backup"])
    assert len(factory.calls) == calls_before_no_candidate

    clock.advance(seconds=reopen_seconds)
    calls_before_reentry = len(factory.calls)
    reentry = await invoke_once(["backup", "primary"])
    assert reentry.server == UNIT_TEST_BACKUP_SERVER
    assert reentry.method == method

    reentry_slice = [
        (server, call_method)
        for server, _, call_method in factory.calls[calls_before_reentry:]
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]
    assert reentry_slice == [
        (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_BACKUP_SERVER, method),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["tools/call", "resources/read"])
@pytest.mark.parametrize(
    ("preferred", "expected_first", "expected_second"),
    [
        (["primary", "backup"], "primary", "backup"),
        (["backup", "primary"], "backup", "primary"),
    ],
)
async def test_cluster_nat_simultaneous_unreachable_reopen_prefers_ordered_candidates(
    method: str,
    preferred: list[str],
    expected_first: str,
    expected_second: str,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=1,
    )
    manager.register("primary", "http://primary.local")
    manager.register("backup", "http://backup.local")

    manager.record_check_result("primary", healthy=False, error="hold primary")
    manager.record_check_result("backup", healthy=False, error="hold backup")

    primary = manager.get("primary")
    backup = manager.get("backup")
    assert primary is not None
    assert backup is not None
    assert primary.status is ServerStatus.UNREACHABLE
    assert backup.status is ServerStatus.UNREACHABLE

    factory.set_failure_script(expected_first, "initialize", ["timeout"])
    factory.set_failure_script(expected_second, "initialize", ["ok"])

    async def invoke_once() -> object:
        if method == "resources/read":
            return await manager.read_resource("att://projects", preferred=preferred)
        return await manager.invoke_tool("att.project.list", preferred=preferred)

    calls_before_closed = len(factory.calls)
    with pytest.raises(MCPInvocationError):
        await invoke_once()
    assert len(factory.calls) == calls_before_closed

    clock.advance(seconds=1)
    calls_before_reopen = len(factory.calls)
    reopened = await invoke_once()
    assert reopened.server == expected_second
    assert reopened.method == method
    reopen_events = manager.list_invocation_events(request_id=reopened.request_id)
    initialize_starts = [
        event.server for event in reopen_events if event.phase == UNIT_TEST_INITIALIZE_START_PHASE
    ]
    assert initialize_starts == [expected_first, expected_second]

    reopen_slice = [
        (server, call_method)
        for server, _, call_method in factory.calls[calls_before_reopen:]
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]
    assert reopen_slice == [
        (expected_second, UNIT_TEST_INITIALIZE_METHOD),
        (expected_second, method),
    ]


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
    assert correlated_events[0].server == UNIT_TEST_CODEX_SERVER
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

    primary_invocation = manager.list_invocation_events(
        server=UNIT_TEST_PRIMARY_SERVER,
        request_id=request_id,
    )
    assert [event.phase for event in primary_invocation] == [
        UNIT_TEST_INITIALIZE_START_PHASE,
        UNIT_TEST_INITIALIZE_FAILURE_PHASE,
    ]

    latest_invocation = manager.list_invocation_events(limit=2)
    assert [event.phase for event in latest_invocation] == [
        UNIT_TEST_INVOKE_START_PHASE,
        UNIT_TEST_INVOKE_SUCCESS_PHASE,
    ]

    correlated_connection = manager.list_events(correlation_id=request_id)
    assert len(correlated_connection) == 1
    assert correlated_connection[0].server == UNIT_TEST_PRIMARY_SERVER

    backup_connection = manager.list_events(server=UNIT_TEST_BACKUP_SERVER)
    assert len(backup_connection) == 1
    assert backup_connection[0].correlation_id is None

    latest_connection = manager.list_events(limit=1)
    assert len(latest_connection) == 1
    assert latest_connection[0].server == UNIT_TEST_BACKUP_SERVER
