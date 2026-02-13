from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from att.mcp.client import (
    ExternalServer,
    JSONObject,
    MCPClientManager,
    MCPInvocationError,
    MCPTransportError,
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
