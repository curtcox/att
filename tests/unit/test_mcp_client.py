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
UNIT_TEST_INVALID_PAYLOAD_ERROR_CATEGORY = "invalid_payload"
UNIT_TEST_INITIALIZE_METHOD = "initialize"
UNIT_TEST_TOOLS_CALL_METHOD = "tools/call"
UNIT_TEST_RESOURCES_READ_METHOD = "resources/read"
UNIT_TEST_CLUSTER_NAT_METHOD_VECTOR = (
    UNIT_TEST_TOOLS_CALL_METHOD,
    UNIT_TEST_RESOURCES_READ_METHOD,
)
UNIT_TEST_CLUSTER_NAT_FAILURE_EXHAUSTION_METHOD_MATRIX = (
    (UNIT_TEST_INITIALIZE_METHOD, UNIT_TEST_TOOLS_CALL_METHOD),
    (UNIT_TEST_TOOLS_CALL_METHOD, UNIT_TEST_TOOLS_CALL_METHOD),
    (UNIT_TEST_RESOURCES_READ_METHOD, UNIT_TEST_RESOURCES_READ_METHOD),
)
UNIT_TEST_CLUSTER_NAT_FAILURE_COUNT_STATUS_MATRIX = (
    (1, ServerStatus.DEGRADED),
    (2, ServerStatus.UNREACHABLE),
)
UNIT_TEST_CLUSTER_NAT_UNREACHABLE_AFTER_STATUS_MATRIX = (
    (3, ServerStatus.DEGRADED),
    (1, ServerStatus.UNREACHABLE),
)
UNIT_TEST_CLUSTER_NAT_BACKUP_REOPEN_STATUS_MATRIX = (
    (1, 1, ServerStatus.DEGRADED),
    (2, 2, ServerStatus.UNREACHABLE),
)
UNIT_TEST_CLUSTER_NAT_TRIGGER_VECTOR = (
    "stale_expiry",
    "degraded_status",
)
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
UNIT_TEST_GITHUB_SERVER = "github"
UNIT_TEST_TERMINAL_SERVER = "terminal"
UNIT_TEST_CLUSTER_NAT_MIXED_SCRIPTED_FAILOVER_CALL_ORDER = (
    (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
    (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_TOOLS_CALL_METHOD),
    (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_INITIALIZE_METHOD),
    (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD),
    (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_RESOURCES_READ_METHOD),
    (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
    (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD),
)
UNIT_TEST_CLUSTER_NAT_REPEATED_INVOKES_PROGRESSIONS = (
    (
        UNIT_TEST_TOOLS_CALL_METHOD,
        (
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_TOOLS_CALL_METHOD,
            UNIT_TEST_TOOLS_CALL_METHOD,
        ),
        (
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_TOOLS_CALL_METHOD,
            UNIT_TEST_TOOLS_CALL_METHOD,
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_TOOLS_CALL_METHOD,
        ),
    ),
    (
        UNIT_TEST_RESOURCES_READ_METHOD,
        (
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_RESOURCES_READ_METHOD,
            UNIT_TEST_RESOURCES_READ_METHOD,
        ),
        (
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_RESOURCES_READ_METHOD,
            UNIT_TEST_RESOURCES_READ_METHOD,
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_RESOURCES_READ_METHOD,
        ),
    ),
)
UNIT_TEST_CLUSTER_NAT_FORCE_REINITIALIZE_REENTRY_CALL_ORDERS = (
    (
        UNIT_TEST_TOOLS_CALL_METHOD,
        (
            (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
            (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_TOOLS_CALL_METHOD),
            (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
            (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_TOOLS_CALL_METHOD),
        ),
    ),
    (
        UNIT_TEST_RESOURCES_READ_METHOD,
        (
            (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
            (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD),
            (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD),
            (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD),
        ),
    ),
)
UNIT_TEST_CLUSTER_NAT_FORCE_REINITIALIZE_REENTRY_CALL_ORDER_LISTS = {
    method_name: list(call_order_vector)
    for method_name, call_order_vector in (
        UNIT_TEST_CLUSTER_NAT_FORCE_REINITIALIZE_REENTRY_CALL_ORDERS
    )
}
UNIT_TEST_CLUSTER_NAT_PREFERRED_REOPEN_MATRIX = (
    (
        [UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_BACKUP_SERVER],
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_BACKUP_SERVER,
    ),
    (
        [UNIT_TEST_BACKUP_SERVER, UNIT_TEST_PRIMARY_SERVER],
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_PRIMARY_SERVER,
    ),
)
UNIT_TEST_CLUSTER_NAT_REOPEN_INITIALIZE_START_SERVER_ORDERS = {
    tuple(preferred): [expected_first, expected_second]
    for preferred, expected_first, expected_second in UNIT_TEST_CLUSTER_NAT_PREFERRED_REOPEN_MATRIX
}
UNIT_TEST_INITIALIZE_START_PHASE = "initialize_start"
UNIT_TEST_INITIALIZE_FAILURE_PHASE = "initialize_failure"
UNIT_TEST_INITIALIZE_SUCCESS_PHASE = "initialize_success"
UNIT_TEST_INVOKE_STAGE = "invoke"
UNIT_TEST_INVOKE_START_PHASE = "invoke_start"
UNIT_TEST_INVOKE_FAILURE_PHASE = "invoke_failure"
UNIT_TEST_INVOKE_SUCCESS_PHASE = "invoke_success"
UNIT_TEST_INITIALIZE_START_FAILURE_PHASES = (
    UNIT_TEST_INITIALIZE_START_PHASE,
    UNIT_TEST_INITIALIZE_FAILURE_PHASE,
)
UNIT_TEST_INVOKE_START_SUCCESS_PHASES = (
    UNIT_TEST_INVOKE_START_PHASE,
    UNIT_TEST_INVOKE_SUCCESS_PHASE,
)
UNIT_TEST_SESSION_ID_FIRST = "session-1"
UNIT_TEST_SESSION_ID_SECOND = "session-2"
UNIT_TEST_PROTOCOL_VERSION = "2025-11-25"
UNIT_TEST_PROJECTS_URI = "att://projects"
UNIT_TEST_PROJECT_LIST_TOOL_NAME = "att.project.list"
UNIT_TEST_FRESHNESS_UNKNOWN = "unknown"
UNIT_TEST_FRESHNESS_ACTIVE_RECENT = "active_recent"
UNIT_TEST_FRESHNESS_STALE = "stale"
UNIT_TEST_SESSION_CALL_ENTRY_LABEL = "session"
UNIT_TEST_TOOL_CALL_ENTRY_LABEL = "tool"
UNIT_TEST_RESOURCE_CALL_ENTRY_LABEL = "resource"
UNIT_TEST_ERROR_DOWN = "down"
UNIT_TEST_ERROR_SLOW = "slow"
UNIT_TEST_ERROR_HOLD_BACKUP = "hold backup"
UNIT_TEST_ERROR_HOLD_PRIMARY = "hold primary"
UNIT_TEST_ERROR_MANUAL_DEGRADE = "manual degrade"
UNIT_TEST_ERROR_TIMEOUT = "timeout"
UNIT_TEST_ERROR_TEMPORARY = "temporary"
UNIT_TEST_ERROR_INIT_FAILED = "init failed"
UNIT_TEST_ERROR_CONNECT_TIMEOUT = "connect timeout"
UNIT_TEST_ERROR_PRIMARY_UNAVAILABLE = "primary unavailable"
UNIT_TEST_ERROR_PRIMARY_DOWN = "primary down"
UNIT_TEST_ERROR_INIT_DOWN = "init down"
UNIT_TEST_ERROR_HTTP_STATUS_503 = "http status 503"
UNIT_TEST_ERROR_BAD_STATUS = "bad status"
UNIT_TEST_ERROR_RPC_DOWN = "rpc down"
UNIT_TEST_ERROR_RPC_FAILURE = "rpc failure"
UNIT_TEST_ERROR_RPC_FAILURE_WITH_PREFIX = "rpc error: rpc failure"
UNIT_TEST_ERROR_TIMED_OUT = "timed out"
UNIT_TEST_ERROR_BAD_PAYLOAD = "bad payload"
UNIT_TEST_NAT_TOOL_REQUEST_ID = "tool-1"
UNIT_TEST_NAT_INITIALIZE_REQUEST_ID = "init-1"
UNIT_TEST_NAT_INITIALIZED_NOTIFICATION_REQUEST_ID = "init-notify"
UNIT_TEST_NAT_RESOURCE_READ_REQUEST_ID = "resource-1"
UNIT_TEST_HTTP_METHOD_POST = "POST"
UNIT_TEST_NAT_MCP_ENDPOINT = "http://nat.local/mcp"
UNIT_TEST_NAT_CATEGORY_MAPPING_FAILURE_MATRIX = (
    (
        httpx.ReadTimeout(UNIT_TEST_ERROR_TIMED_OUT),
        UNIT_TEST_TIMEOUT_ERROR_CATEGORY,
    ),
    (
        httpx.HTTPStatusError(
            UNIT_TEST_ERROR_BAD_STATUS,
            request=httpx.Request(UNIT_TEST_HTTP_METHOD_POST, UNIT_TEST_NAT_MCP_ENDPOINT),
            response=httpx.Response(
                503,
                request=httpx.Request(UNIT_TEST_HTTP_METHOD_POST, UNIT_TEST_NAT_MCP_ENDPOINT),
            ),
        ),
        UNIT_TEST_HTTP_STATUS_ERROR_CATEGORY,
    ),
    (ValueError(UNIT_TEST_ERROR_BAD_PAYLOAD), UNIT_TEST_INVALID_PAYLOAD_ERROR_CATEGORY),
)
UNIT_TEST_NAT_SERVER_URL = "http://nat.local"
UNIT_TEST_SERVER_A_URL = "http://a.local"
UNIT_TEST_SERVER_B_URL = "http://b.local"
UNIT_TEST_SERVER_C_URL = "http://c.local"
UNIT_TEST_CODEX_SERVER_URL = "http://codex.local"
UNIT_TEST_GITHUB_SERVER_URL = "http://github.local"
UNIT_TEST_SECONDARY_SERVER_URL = "http://secondary.local"
UNIT_TEST_RECOVERED_SERVER_URL = "http://recovered.local"
UNIT_TEST_DEGRADED_SERVER_URL = "http://degraded.local"
UNIT_TEST_PRIMARY_SERVER_URL = "http://primary.local"
UNIT_TEST_BACKUP_SERVER_URL = "http://backup.local"
UNIT_TEST_TERMINAL_SERVER_URL = "http://terminal.local"
UNIT_TEST_PRIMARY_ENDPOINT_HOST_FRAGMENT = "primary.local"
UNIT_TEST_RECOVERED_ENDPOINT_HOST_FRAGMENT = "recovered.local"
UNIT_TEST_ADAPTER_SESSION_STALE_AFTER_SECONDS = 60
UNIT_TEST_ADAPTER_SESSION_STALE_DELTA_SECONDS = 61
UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR = ("ok",)
UNIT_TEST_FAILURE_SCRIPT_ERROR_VECTOR = ("error",)
UNIT_TEST_FAILURE_SCRIPT_ERROR_OK_VECTOR = ("error", "ok")
UNIT_TEST_FAILURE_SCRIPT_INVALID_VECTOR = ("invalid",)
UNIT_TEST_FAILURE_SCRIPT_OK_TIMEOUT_ERROR_VECTOR = ("ok", "timeout", "error")
UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_VECTOR = ("timeout",)
UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_OK_VECTOR = ("timeout", "ok")
UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_TIMEOUT_OK_VECTOR = ("timeout", "timeout", "ok")
UNIT_TEST_FAILURE_ACTION_ERROR = "error"
UNIT_TEST_FAILURE_ACTION_OK = "ok"
UNIT_TEST_FAILURE_ACTION_TIMEOUT = "timeout"
UNIT_TEST_GITHUB_SERVER_INFO = {"name": "github", "version": "2.0.0"}
UNIT_TEST_SERVER_A_B_VECTOR = (UNIT_TEST_SERVER_A, UNIT_TEST_SERVER_B)
UNIT_TEST_SERVER_C_VECTOR = (UNIT_TEST_SERVER_C,)
UNIT_TEST_PRIMARY_INITIALIZE_CALL_ORDER_ENTRY = (
    UNIT_TEST_PRIMARY_SERVER,
    UNIT_TEST_INITIALIZE_METHOD,
)
UNIT_TEST_BACKUP_INITIALIZE_CALL_ORDER_ENTRY = (
    UNIT_TEST_BACKUP_SERVER,
    UNIT_TEST_INITIALIZE_METHOD,
)


def _unit_test_primary_method_call_order_entry(method: str) -> tuple[str, str]:
    return (UNIT_TEST_PRIMARY_SERVER, method)


def _unit_test_backup_method_call_order_entry(method: str) -> tuple[str, str]:
    return (UNIT_TEST_BACKUP_SERVER, method)


def _unit_test_primary_reentry_call_order_slice(method: str) -> list[tuple[str, str]]:
    return [
        UNIT_TEST_PRIMARY_INITIALIZE_CALL_ORDER_ENTRY,
        _unit_test_primary_method_call_order_entry(method),
    ]


def _unit_test_backup_reentry_call_order_slice(method: str) -> list[tuple[str, str]]:
    return [
        UNIT_TEST_BACKUP_INITIALIZE_CALL_ORDER_ENTRY,
        _unit_test_backup_method_call_order_entry(method),
    ]


def _assert_unit_test_primary_reentry_slice(
    observed_slice: list[tuple[str, str]],
    method: str,
) -> None:
    assert observed_slice == _unit_test_primary_reentry_call_order_slice(method)


def _assert_unit_test_backup_reentry_slice(
    observed_slice: list[tuple[str, str]],
    method: str,
) -> None:
    assert observed_slice == _unit_test_backup_reentry_call_order_slice(method)


UNIT_TEST_PRIMARY_RESOURCE_REENTRY_CALL_ORDER_SLICE = (
    UNIT_TEST_PRIMARY_INITIALIZE_CALL_ORDER_ENTRY,
    (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_RESOURCES_READ_METHOD),
)


def _unit_test_collect_reentry_call_order_slice(
    calls: list[tuple[str, str, str]],
    start_index: int,
    method: str,
) -> list[tuple[str, str]]:
    return [
        (server, call_method)
        for server, _, call_method in calls[start_index:]
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]


def _unit_test_collect_full_call_order_slice(
    calls: list[tuple[str, str, str]],
    start_index: int,
    method: str,
) -> list[tuple[str, str, str]]:
    return [
        (server, session_id, call_method)
        for server, session_id, call_method in calls[start_index:]
        if call_method in {UNIT_TEST_INITIALIZE_METHOD, method}
    ]


def _unit_test_collect_mixed_method_call_order_slice(
    calls: list[tuple[str, str, str]],
    start_index: int,
) -> list[tuple[str, str]]:
    return [
        (server, method)
        for server, _, method in calls[start_index:]
        if method
        in {
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_TOOLS_CALL_METHOD,
            UNIT_TEST_RESOURCES_READ_METHOD,
        }
    ]


def _assert_unit_test_collected_primary_reentry_slice(
    calls: list[tuple[str, str, str]],
    start_index: int,
    method: str,
) -> None:
    _assert_unit_test_primary_reentry_slice(
        _unit_test_collect_reentry_call_order_slice(calls, start_index, method),
        method,
    )


def _assert_unit_test_collected_backup_reentry_slice(
    calls: list[tuple[str, str, str]],
    start_index: int,
    method: str,
) -> None:
    _assert_unit_test_backup_reentry_slice(
        _unit_test_collect_reentry_call_order_slice(calls, start_index, method),
        method,
    )


def _assert_unit_test_reopen_slice(
    observed_slice: list[tuple[str, str]],
    expected_server: str,
    method: str,
) -> None:
    assert observed_slice == [
        (expected_server, UNIT_TEST_INITIALIZE_METHOD),
        (expected_server, method),
    ]


def _assert_unit_test_failure_script_state_snapshot(
    factory: ClusterNatSessionFactory,
    backup_tools_call_vector: tuple[str, ...],
) -> None:
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
        backup_tools_call_vector
    )


def _assert_unit_test_failure_script_terminal_state(
    factory: ClusterNatSessionFactory,
) -> None:
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


def _assert_unit_test_failure_script_method_exhausted(
    factory: ClusterNatSessionFactory,
    server: str,
    method: str,
) -> None:
    assert factory.consume_failure_action(server, method) is None


def _assert_unit_test_failure_script_consumed_action(
    factory: ClusterNatSessionFactory,
    server: str,
    method: str,
    expected_action: str,
) -> None:
    assert factory.consume_failure_action(server, method) == expected_action


def _set_unit_test_failure_script(
    factory: ClusterNatSessionFactory,
    server: str,
    method: str,
    setup_vector: tuple[str, ...],
) -> None:
    factory.set_failure_script(server, method, list(setup_vector))


def _assert_unit_test_failure_script_progression(
    factory: ClusterNatSessionFactory,
    server: str,
    method: str,
    setup_vector: tuple[str, ...],
    consumed_actions: tuple[str, ...],
) -> None:
    _set_unit_test_failure_script(factory, server, method, setup_vector)
    for expected_action in consumed_actions:
        _assert_unit_test_failure_script_consumed_action(
            factory,
            server,
            method,
            expected_action,
        )
    _assert_unit_test_failure_script_method_exhausted(factory, server, method)


@pytest.mark.asyncio
async def test_health_check_probe_updates_status_and_logs_transition() -> None:
    async def flaky_probe(_: object) -> tuple[bool, str | None]:
        return False, UNIT_TEST_ERROR_TIMEOUT

    clock = MCPTestClock()
    manager = MCPClientManager(
        probe=flaky_probe,
        unreachable_after=2,
        now_provider=clock,
    )
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

    await manager.health_check_server("codex")
    server = manager.get(UNIT_TEST_CODEX_SERVER)
    assert server is not None
    assert server.status is ServerStatus.DEGRADED
    assert server.retry_count == 1
    assert server.last_error == UNIT_TEST_ERROR_TIMEOUT
    clock.advance(seconds=1)

    await manager.health_check_server("codex")
    server = manager.get(UNIT_TEST_CODEX_SERVER)
    assert server is not None
    assert server.status is ServerStatus.UNREACHABLE
    assert server.retry_count == 2

    events = manager.list_events()
    assert len(events) == 2
    assert events[0].to_status is ServerStatus.DEGRADED
    assert events[1].to_status is ServerStatus.UNREACHABLE


@pytest.mark.asyncio
async def test_health_check_recovery_resets_backoff() -> None:
    states = [(False, UNIT_TEST_ERROR_TEMPORARY), (True, None)]

    async def toggled_probe(_: object) -> tuple[bool, str | None]:
        return states.pop(0)

    manager = MCPClientManager(probe=toggled_probe)
    manager.register("github", UNIT_TEST_GITHUB_SERVER_URL)

    await manager.health_check_server("github")
    degraded = manager.get(UNIT_TEST_GITHUB_SERVER)
    assert degraded is not None
    assert degraded.status is ServerStatus.DEGRADED
    assert degraded.next_retry_at is not None

    manager.record_check_result(UNIT_TEST_GITHUB_SERVER, healthy=True)
    recovered = manager.get(UNIT_TEST_GITHUB_SERVER)
    assert recovered is not None
    assert recovered.status is ServerStatus.HEALTHY
    assert recovered.retry_count == 0
    assert recovered.next_retry_at is None


@pytest.mark.asyncio
async def test_should_retry_observes_next_retry_window() -> None:
    manager = MCPClientManager()
    manager.register("terminal", UNIT_TEST_TERMINAL_SERVER_URL)

    now = datetime.now(UTC)
    manager.record_check_result(
        UNIT_TEST_TERMINAL_SERVER,
        healthy=False,
        error=UNIT_TEST_ERROR_DOWN,
        checked_at=now,
    )

    assert manager.should_retry(UNIT_TEST_TERMINAL_SERVER, now=now) is False
    assert manager.should_retry(UNIT_TEST_TERMINAL_SERVER, now=now + timedelta(seconds=1)) is True


@pytest.mark.asyncio
async def test_should_retry_uses_injected_clock_when_now_omitted() -> None:
    clock = MCPTestClock()
    manager = MCPClientManager(now_provider=clock)
    manager.register("terminal", UNIT_TEST_TERMINAL_SERVER_URL)
    manager.record_check_result(
        UNIT_TEST_TERMINAL_SERVER, healthy=False, error=UNIT_TEST_ERROR_DOWN
    )

    assert manager.should_retry(UNIT_TEST_TERMINAL_SERVER) is False
    clock.advance(seconds=1)
    assert manager.should_retry(UNIT_TEST_TERMINAL_SERVER) is True


def test_choose_server_prefers_healthy_then_degraded() -> None:
    manager = MCPClientManager()
    manager.register("a", UNIT_TEST_SERVER_A_URL)
    manager.register("b", UNIT_TEST_SERVER_B_URL)

    manager.record_check_result(UNIT_TEST_SERVER_A, healthy=False, error=UNIT_TEST_ERROR_SLOW)

    selected = manager.choose_server()
    assert selected is not None
    assert selected.name == UNIT_TEST_SERVER_B

    manager.record_check_result(UNIT_TEST_SERVER_B, healthy=False, error=UNIT_TEST_ERROR_DOWN)
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
            raise RuntimeError(UNIT_TEST_ERROR_CONNECT_TIMEOUT)
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"ok": True, "method": str(request.get("method", ""))},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)

    result = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME,
        {"limit": 10},
        preferred=["primary", "backup"],
    )
    assert result.server == UNIT_TEST_BACKUP_SERVER
    assert result.method == UNIT_TEST_TOOLS_CALL_METHOD
    assert isinstance(result.result, dict)
    assert result.result["ok"] is True
    assert calls[0] == (UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)
    assert calls[-1] == (UNIT_TEST_BACKUP_SERVER, UNIT_TEST_TOOLS_CALL_METHOD)

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
    backup = manager.get(UNIT_TEST_BACKUP_SERVER)
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
                "error": {"message": UNIT_TEST_ERROR_RPC_DOWN},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"uri": UNIT_TEST_PROJECTS_URI},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("secondary", UNIT_TEST_SECONDARY_SERVER_URL)

    result = await manager.read_resource(
        UNIT_TEST_PROJECTS_URI,
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
        await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME)
    assert exc_info.value.method == UNIT_TEST_TOOLS_CALL_METHOD
    assert exc_info.value.attempts == []


@pytest.mark.asyncio
async def test_invoke_tool_error_contains_structured_attempt_trace() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if server.name == "primary":
            raise RuntimeError(UNIT_TEST_ERROR_PRIMARY_DOWN)
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "error": {"message": UNIT_TEST_ERROR_RPC_FAILURE},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)

    with pytest.raises(MCPInvocationError) as exc_info:
        await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["primary", "backup"])

    error = exc_info.value
    assert error.method == UNIT_TEST_TOOLS_CALL_METHOD
    assert len(error.attempts) == 3
    assert error.attempts[0].server == UNIT_TEST_PRIMARY_SERVER
    assert error.attempts[0].stage == UNIT_TEST_INITIALIZE_METHOD
    assert error.attempts[0].success is False
    assert error.attempts[0].error == UNIT_TEST_ERROR_PRIMARY_DOWN
    assert error.attempts[0].error_category == UNIT_TEST_TRANSPORT_ERROR_CATEGORY
    assert error.attempts[1].server == UNIT_TEST_BACKUP_SERVER
    assert error.attempts[1].stage == UNIT_TEST_INITIALIZE_METHOD
    assert error.attempts[1].success is True
    assert error.attempts[1].error_category is None
    assert error.attempts[2].server == UNIT_TEST_BACKUP_SERVER
    assert error.attempts[2].stage == UNIT_TEST_INVOKE_STAGE
    assert error.attempts[2].success is False
    assert error.attempts[2].error == UNIT_TEST_ERROR_RPC_FAILURE_WITH_PREFIX
    assert error.attempts[2].error_category == UNIT_TEST_RPC_ERROR_CATEGORY


@pytest.mark.asyncio
async def test_invoke_tool_reinitializes_when_initialization_is_stale() -> None:
    calls: list[str] = []

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        calls.append(method)
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
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
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

    await manager.initialize_server(UNIT_TEST_CODEX_SERVER)
    result = await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME)

    assert result.server == UNIT_TEST_CODEX_SERVER
    assert calls == [
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD,
        UNIT_TEST_TOOLS_CALL_METHOD,
    ]
    server = manager.get(UNIT_TEST_CODEX_SERVER)
    assert server is not None
    assert server.initialization_expires_at is not None


@pytest.mark.asyncio
async def test_invoke_tool_transport_error_category_http_status() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        raise MCPTransportError(
            UNIT_TEST_ERROR_HTTP_STATUS_503,
            category=UNIT_TEST_HTTP_STATUS_ERROR_CATEGORY,
        )

    manager = MCPClientManager(transport=transport)
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

    with pytest.raises(MCPInvocationError) as exc_info:
        await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME)

    error = exc_info.value
    assert len(error.attempts) == 2
    assert error.attempts[1].stage == UNIT_TEST_INVOKE_STAGE
    assert error.attempts[1].error_category == UNIT_TEST_HTTP_STATUS_ERROR_CATEGORY
    server = manager.get(UNIT_TEST_CODEX_SERVER)
    assert server is not None
    assert server.last_error_category == UNIT_TEST_HTTP_STATUS_ERROR_CATEGORY


@pytest.mark.asyncio
async def test_invoke_tool_mixed_state_cluster_recovers_in_preferred_order() -> None:
    calls: list[tuple[str, str]] = []
    clock = MCPTestClock()

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        calls.append((server.name, method))
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {},
            }
        if server.name == "primary":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "error": {"message": UNIT_TEST_ERROR_RPC_FAILURE},
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("recovered", UNIT_TEST_RECOVERED_SERVER_URL)
    manager.register("degraded", UNIT_TEST_DEGRADED_SERVER_URL)

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
    assert primary is not None
    primary.status = ServerStatus.HEALTHY
    primary.initialized = True
    primary.last_initialized_at = clock.current
    primary.initialization_expires_at = clock.current + timedelta(seconds=60)

    recovered = manager.get(UNIT_TEST_RECOVERED_SERVER)
    assert recovered is not None
    recovered.status = ServerStatus.HEALTHY
    recovered.initialized = False

    manager.record_check_result(
        UNIT_TEST_DEGRADED_SERVER, healthy=False, error=UNIT_TEST_ERROR_DOWN
    )
    clock.advance(seconds=2)

    result = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME,
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
    updated_primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
    updated_recovered = manager.get(UNIT_TEST_RECOVERED_SERVER)
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
            raise RuntimeError(UNIT_TEST_ERROR_PRIMARY_UNAVAILABLE)
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)

    result = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["primary", "backup"]
    )
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
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
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
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

    await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME)

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
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {
                    "protocolVersion": "2025-11-25",
                    "serverInfo": {"name": "codex", "version": "1.0.0"},
                    "capabilities": {"tools": {}, "resources": {}},
                },
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
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
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

    initialized = await manager.initialize_server(UNIT_TEST_CODEX_SERVER)

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
        raise RuntimeError(UNIT_TEST_ERROR_INIT_FAILED)

    manager = MCPClientManager(transport=transport)
    manager.register("github", UNIT_TEST_GITHUB_SERVER_URL)

    initialized = await manager.initialize_server(UNIT_TEST_GITHUB_SERVER)

    assert initialized is not None
    assert initialized.status is ServerStatus.DEGRADED
    assert initialized.initialized is False
    assert initialized.last_error == UNIT_TEST_ERROR_INIT_FAILED


@pytest.mark.asyncio
async def test_initialize_server_failure_preserves_last_capability_snapshot() -> None:
    calls = 0

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        nonlocal calls
        method = str(request.get("method", ""))
        if method == UNIT_TEST_INITIALIZE_METHOD:
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
            raise RuntimeError(UNIT_TEST_ERROR_INIT_FAILED)
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("github", UNIT_TEST_GITHUB_SERVER_URL)

    first = await manager.initialize_server(UNIT_TEST_GITHUB_SERVER)
    second = await manager.initialize_server(UNIT_TEST_GITHUB_SERVER, force=True)

    assert first is not None
    assert first.capability_snapshot is not None
    assert first.capability_snapshot.server_info == UNIT_TEST_GITHUB_SERVER_INFO

    assert second is not None
    assert second.initialized is False
    assert second.status is ServerStatus.DEGRADED
    assert second.capability_snapshot is not None
    assert second.capability_snapshot.server_info == UNIT_TEST_GITHUB_SERVER_INFO


@pytest.mark.asyncio
async def test_initialize_all_returns_all_servers() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"protocolVersion": "2025-11-25"},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("a", UNIT_TEST_SERVER_A_URL)
    manager.register("b", UNIT_TEST_SERVER_B_URL)

    results = await manager.initialize_all()

    assert [server.name for server in results] == list(UNIT_TEST_SERVER_A_B_VECTOR)
    assert all(server.initialized for server in results)


@pytest.mark.asyncio
async def test_invoke_tool_auto_initializes_server_before_tool_call() -> None:
    calls: list[str] = []

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        calls.append(method)
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
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
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

    result = await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME)

    assert result.server == UNIT_TEST_CODEX_SERVER
    assert calls == [
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD,
        UNIT_TEST_TOOLS_CALL_METHOD,
    ]
    server = manager.get(UNIT_TEST_CODEX_SERVER)
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
        if method == UNIT_TEST_INITIALIZE_METHOD:
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
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

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
        return False, UNIT_TEST_ERROR_DOWN

    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        transport_calls.append(str(request.get("method", "")))
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {},
        }

    manager = MCPClientManager(probe=probe, transport=transport, unreachable_after=1)
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

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
    server = ExternalServer(name=UNIT_TEST_NAT_SERVER, url=UNIT_TEST_NAT_SERVER_URL)

    initialize = await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": UNIT_TEST_NAT_INITIALIZE_REQUEST_ID,
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
            "id": UNIT_TEST_NAT_INITIALIZED_NOTIFICATION_REQUEST_ID,
            "method": "notifications/initialized",
            "params": {},
        },
    )
    assert initialized["result"] == {}

    tool_call = await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": UNIT_TEST_NAT_TOOL_REQUEST_ID,
            "method": "tools/call",
            "params": {"name": UNIT_TEST_PROJECT_LIST_TOOL_NAME, "arguments": {"limit": 1}},
        },
    )
    assert isinstance(tool_call["result"], dict)
    assert tool_call["result"]["isError"] is False

    resource_read = await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": UNIT_TEST_NAT_RESOURCE_READ_REQUEST_ID,
            "method": "resources/read",
            "params": {"uri": UNIT_TEST_PROJECTS_URI},
        },
    )
    assert isinstance(resource_read["result"], dict)
    assert resource_read["result"]["contents"][0]["uri"] == UNIT_TEST_PROJECTS_URI
    assert session.calls == [
        (UNIT_TEST_SESSION_CALL_ENTRY_LABEL, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_SESSION_CALL_ENTRY_LABEL, UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD),
        (UNIT_TEST_TOOL_CALL_ENTRY_LABEL, UNIT_TEST_PROJECT_LIST_TOOL_NAME),
        (UNIT_TEST_RESOURCE_CALL_ENTRY_LABEL, UNIT_TEST_PROJECTS_URI),
    ]


@pytest.mark.asyncio
async def test_nat_transport_adapter_session_diagnostics_and_invalidate() -> None:
    session = FakeNatSession()

    @asynccontextmanager
    async def session_context(_: str) -> Any:
        yield session

    adapter = NATMCPTransportAdapter(session_factory=session_context)
    server = ExternalServer(name=UNIT_TEST_NAT_SERVER, url=UNIT_TEST_NAT_SERVER_URL)

    before = adapter.session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert before.active is False
    assert before.initialized is False
    assert before.last_activity_at is None

    await adapter(
        server,
        {
            "jsonrpc": "2.0",
            "id": UNIT_TEST_NAT_TOOL_REQUEST_ID,
            "method": "tools/call",
            "params": {"name": UNIT_TEST_PROJECT_LIST_TOOL_NAME, "arguments": {}},
        },
    )

    after = adapter.session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert after.active is True
    assert after.initialized is True
    assert after.last_activity_at is not None

    invalidated = await adapter.invalidate_session(UNIT_TEST_NAT_SERVER)
    assert invalidated is True

    final = adapter.session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert final.active is False
    assert final.initialized is False
    assert final.last_activity_at is None


@pytest.mark.asyncio
async def test_manager_adapter_session_controls_invalidate_and_refresh() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register(UNIT_TEST_NAT_SERVER, UNIT_TEST_NAT_SERVER_URL)

    assert manager.supports_adapter_session_controls() is True
    diagnostics = manager.adapter_session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert diagnostics is not None
    assert diagnostics.active is False

    initialized = await manager.initialize_server(UNIT_TEST_NAT_SERVER)
    assert initialized is not None
    assert initialized.initialized is True
    assert factory.created == 1

    after_initialize = manager.adapter_session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert after_initialize is not None
    assert after_initialize.active is True
    assert after_initialize.initialized is True
    assert after_initialize.last_activity_at is not None

    invalidated = await manager.invalidate_adapter_session(UNIT_TEST_NAT_SERVER)
    assert invalidated is True
    assert factory.closed == 1
    server = manager.get(UNIT_TEST_NAT_SERVER)
    assert server is not None
    assert server.initialized is False

    refreshed = await manager.refresh_adapter_session(UNIT_TEST_NAT_SERVER)
    assert refreshed is not None
    assert refreshed.initialized is True
    assert factory.created == 2


@pytest.mark.asyncio
async def test_manager_adapter_session_controls_absent_for_non_nat_adapter() -> None:
    manager = MCPClientManager(transport_adapter=FakeNatSession())  # type: ignore[arg-type]
    manager.register(UNIT_TEST_NAT_SERVER, UNIT_TEST_NAT_SERVER_URL)

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
    manager.register("b", UNIT_TEST_SERVER_B_URL)
    manager.register("a", UNIT_TEST_SERVER_A_URL)

    before = manager.list_adapter_sessions()
    assert [item.server for item in before] == list(UNIT_TEST_SERVER_A_B_VECTOR)
    assert all(item.active is False for item in before)

    await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["b"])

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
    manager.register("a", UNIT_TEST_SERVER_A_URL)
    manager.register("b", UNIT_TEST_SERVER_B_URL)
    manager.register("c", UNIT_TEST_SERVER_C_URL)

    await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["a"])
    await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["c"])

    active_only = manager.list_adapter_sessions(active_only=True)
    assert [item.server for item in active_only] == [UNIT_TEST_SERVER_A, UNIT_TEST_SERVER_C]

    only_c = manager.list_adapter_sessions(server_name=UNIT_TEST_SERVER_C)
    assert [item.server for item in only_c] == list(UNIT_TEST_SERVER_C_VECTOR)
    assert only_c[0].active is True

    limited = manager.list_adapter_sessions(limit=1)
    assert [item.server for item in limited] == list(UNIT_TEST_SERVER_C_VECTOR)


@pytest.mark.asyncio
async def test_manager_adapter_session_freshness_semantics() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        adapter_session_stale_after_seconds=300,
    )
    manager.register(UNIT_TEST_NAT_SERVER, UNIT_TEST_NAT_SERVER_URL)

    initial = manager.adapter_session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert initial is not None
    assert initial.freshness == UNIT_TEST_FRESHNESS_UNKNOWN

    await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=[UNIT_TEST_NAT_SERVER])

    recent = manager.adapter_session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert recent is not None
    assert recent.active is True
    assert recent.freshness == UNIT_TEST_FRESHNESS_ACTIVE_RECENT

    adapter = manager._adapter_with_session_controls()
    assert adapter is not None
    adapter._sessions[UNIT_TEST_NAT_SERVER].last_activity_at = datetime.now(UTC) - timedelta(
        seconds=301
    )

    stale = manager.adapter_session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert stale is not None
    assert stale.freshness == UNIT_TEST_FRESHNESS_STALE

    listing = manager.list_adapter_sessions(server_name=UNIT_TEST_NAT_SERVER)
    assert len(listing) == 1
    assert listing[0].freshness == UNIT_TEST_FRESHNESS_STALE


@pytest.mark.asyncio
async def test_manager_list_adapter_sessions_supports_freshness_filter() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        adapter_session_stale_after_seconds=UNIT_TEST_ADAPTER_SESSION_STALE_AFTER_SECONDS,
    )
    manager.register(UNIT_TEST_SERVER_A, UNIT_TEST_SERVER_A_URL)
    manager.register(UNIT_TEST_SERVER_B, UNIT_TEST_SERVER_B_URL)

    await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME,
        preferred=[UNIT_TEST_SERVER_A],
    )

    adapter = manager._adapter_with_session_controls()
    assert adapter is not None
    adapter._sessions[UNIT_TEST_SERVER_A].last_activity_at = datetime.now(UTC) - timedelta(
        seconds=UNIT_TEST_ADAPTER_SESSION_STALE_DELTA_SECONDS,
    )

    stale = manager.list_adapter_sessions(freshness=UNIT_TEST_FRESHNESS_STALE)
    assert [item.server for item in stale] == [UNIT_TEST_SERVER_A]

    unknown = manager.list_adapter_sessions(freshness=UNIT_TEST_FRESHNESS_UNKNOWN)
    assert [item.server for item in unknown] == [UNIT_TEST_SERVER_B]

    recent = manager.list_adapter_sessions(freshness=UNIT_TEST_FRESHNESS_ACTIVE_RECENT)
    assert recent == []


@pytest.mark.asyncio
async def test_refresh_adapter_session_recreates_underlying_session_identity() -> None:
    factory = FakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register(UNIT_TEST_NAT_SERVER, UNIT_TEST_NAT_SERVER_URL)

    first = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME,
        preferred=[UNIT_TEST_NAT_SERVER],
    )
    assert isinstance(first.result, dict)
    first_session_id = first.result["structuredContent"]["session_id"]
    assert first_session_id == UNIT_TEST_SESSION_ID_FIRST

    refreshed = await manager.refresh_adapter_session(UNIT_TEST_NAT_SERVER)
    assert refreshed is not None
    assert factory.created == 2
    assert factory.closed == 1
    assert factory.sessions[0] is not factory.sessions[1]

    second = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME,
        preferred=[UNIT_TEST_NAT_SERVER],
    )
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
            if session.session_id == UNIT_TEST_SESSION_ID_FIRST:
                session.fail_with = httpx.ReadTimeout(UNIT_TEST_ERROR_TIMED_OUT)
            yield session

    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=session_context),
        max_backoff_seconds=0,
    )
    manager.register(UNIT_TEST_NAT_SERVER, UNIT_TEST_NAT_SERVER_URL)

    with pytest.raises(MCPInvocationError):
        await manager.invoke_tool(
            UNIT_TEST_PROJECT_LIST_TOOL_NAME,
            preferred=[UNIT_TEST_NAT_SERVER],
        )

    first_diag = manager.adapter_session_diagnostics(UNIT_TEST_NAT_SERVER)
    assert first_diag is not None
    assert first_diag.active is False
    assert factory.created == 1
    assert factory.closed == 1

    retry = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME,
        preferred=[UNIT_TEST_NAT_SERVER],
    )
    assert retry.server == UNIT_TEST_NAT_SERVER
    assert isinstance(retry.result, dict)
    assert retry.result["structuredContent"]["session_id"] == UNIT_TEST_SESSION_ID_SECOND
    assert factory.created == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "category"),
    UNIT_TEST_NAT_CATEGORY_MAPPING_FAILURE_MATRIX,
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
    server = ExternalServer(name=UNIT_TEST_NAT_SERVER, url=UNIT_TEST_NAT_SERVER_URL)

    with pytest.raises(MCPTransportError) as exc_info:
        await adapter(
            server,
            {
                "jsonrpc": "2.0",
                "id": UNIT_TEST_NAT_TOOL_REQUEST_ID,
                "method": "tools/call",
                "params": {"name": UNIT_TEST_PROJECT_LIST_TOOL_NAME, "arguments": {}},
            },
        )
    assert exc_info.value.category == category


@pytest.mark.asyncio
async def test_adapter_transport_fallback_across_mixed_states() -> None:
    sessions: dict[str, FakeNatSession] = {}
    clock = MCPTestClock()

    @asynccontextmanager
    async def session_context(endpoint: str) -> Any:
        if UNIT_TEST_PRIMARY_ENDPOINT_HOST_FRAGMENT in endpoint:
            key = UNIT_TEST_PRIMARY_SERVER
        elif UNIT_TEST_RECOVERED_ENDPOINT_HOST_FRAGMENT in endpoint:
            key = UNIT_TEST_RECOVERED_SERVER
        else:
            key = UNIT_TEST_DEGRADED_SERVER
        session = sessions.setdefault(key, FakeNatSession())
        if key == UNIT_TEST_PRIMARY_SERVER:
            session.fail_with = RuntimeError(UNIT_TEST_ERROR_PRIMARY_UNAVAILABLE)
        yield session

    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=session_context),
        max_initialization_age_seconds=None,
        now_provider=clock,
    )
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("recovered", UNIT_TEST_RECOVERED_SERVER_URL)
    manager.register("degraded", UNIT_TEST_DEGRADED_SERVER_URL)

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
    assert primary is not None
    primary.status = ServerStatus.HEALTHY
    primary.initialized = True
    primary.last_initialized_at = clock.current
    primary.initialization_expires_at = clock.current + timedelta(seconds=60)

    recovered = manager.get(UNIT_TEST_RECOVERED_SERVER)
    assert recovered is not None
    recovered.status = ServerStatus.HEALTHY
    recovered.initialized = False

    manager.record_check_result(
        UNIT_TEST_DEGRADED_SERVER, healthy=False, error=UNIT_TEST_ERROR_DOWN
    )
    clock.advance(seconds=2)

    result = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME,
        preferred=["primary", "recovered", "degraded"],
    )

    assert result.server == UNIT_TEST_RECOVERED_SERVER
    assert sessions[UNIT_TEST_PRIMARY_SERVER].calls == [
        (UNIT_TEST_SESSION_CALL_ENTRY_LABEL, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_TOOL_CALL_ENTRY_LABEL, UNIT_TEST_PROJECT_LIST_TOOL_NAME),
    ]
    assert sessions[UNIT_TEST_RECOVERED_SERVER].calls == [
        (UNIT_TEST_SESSION_CALL_ENTRY_LABEL, UNIT_TEST_INITIALIZE_METHOD),
        (UNIT_TEST_SESSION_CALL_ENTRY_LABEL, UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD),
        (UNIT_TEST_TOOL_CALL_ENTRY_LABEL, UNIT_TEST_PROJECT_LIST_TOOL_NAME),
    ]
    assert UNIT_TEST_DEGRADED_SERVER not in sessions


def test_cluster_nat_failure_script_order_and_validation() -> None:
    factory = ClusterNatSessionFactory()

    _assert_unit_test_failure_script_progression(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_OK_TIMEOUT_ERROR_VECTOR,
        (
            UNIT_TEST_FAILURE_ACTION_OK,
            UNIT_TEST_FAILURE_ACTION_TIMEOUT,
            UNIT_TEST_FAILURE_ACTION_ERROR,
        ),
    )

    _assert_unit_test_failure_script_progression(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_TOOLS_CALL_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR,
        (UNIT_TEST_FAILURE_ACTION_OK,),
    )

    _assert_unit_test_failure_script_progression(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_RESOURCES_READ_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR,
        (UNIT_TEST_FAILURE_ACTION_OK,),
    )

    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_INVALID_VECTOR,
    )
    with pytest.raises(ValueError, match="unsupported scripted action"):
        factory.consume_failure_action(UNIT_TEST_PRIMARY_SERVER, UNIT_TEST_INITIALIZE_METHOD)


def test_cluster_nat_failure_script_isolation_across_servers_and_methods() -> None:
    factory = ClusterNatSessionFactory()

    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_OK_VECTOR,
    )
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_RESOURCES_READ_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_ERROR_VECTOR,
    )
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR,
    )
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_TOOLS_CALL_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_ERROR_OK_VECTOR,
    )

    _assert_unit_test_failure_script_consumed_action(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_ACTION_TIMEOUT,
    )
    _assert_unit_test_failure_script_state_snapshot(
        factory,
        UNIT_TEST_FAILURE_SCRIPT_ERROR_OK_VECTOR,
    )

    _assert_unit_test_failure_script_consumed_action(
        factory,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_TOOLS_CALL_METHOD,
        UNIT_TEST_FAILURE_ACTION_ERROR,
    )
    _assert_unit_test_failure_script_state_snapshot(factory, UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR)

    _assert_unit_test_failure_script_consumed_action(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_RESOURCES_READ_METHOD,
        UNIT_TEST_FAILURE_ACTION_ERROR,
    )
    _assert_unit_test_failure_script_consumed_action(
        factory,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_ACTION_OK,
    )
    _assert_unit_test_failure_script_consumed_action(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_ACTION_OK,
    )
    _assert_unit_test_failure_script_consumed_action(
        factory,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_TOOLS_CALL_METHOD,
        UNIT_TEST_FAILURE_ACTION_OK,
    )

    _assert_unit_test_failure_script_terminal_state(factory)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_key", "expected_method"),
    UNIT_TEST_CLUSTER_NAT_FAILURE_EXHAUSTION_METHOD_MATRIX,
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)

    if method_key == UNIT_TEST_INITIALIZE_METHOD:
        factory.fail_on_timeout_initialize.add(UNIT_TEST_PRIMARY_SERVER)
        _set_unit_test_failure_script(
            factory,
            UNIT_TEST_PRIMARY_SERVER,
            UNIT_TEST_INITIALIZE_METHOD,
            UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR,
        )
    elif method_key == UNIT_TEST_TOOLS_CALL_METHOD:
        factory.fail_on_timeout_tool_calls.add(UNIT_TEST_PRIMARY_SERVER)
        _set_unit_test_failure_script(
            factory,
            UNIT_TEST_PRIMARY_SERVER,
            UNIT_TEST_TOOLS_CALL_METHOD,
            UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR,
        )
    else:
        factory.fail_on_timeout_resource_reads.add(UNIT_TEST_PRIMARY_SERVER)
        _set_unit_test_failure_script(
            factory,
            UNIT_TEST_PRIMARY_SERVER,
            UNIT_TEST_RESOURCES_READ_METHOD,
            UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR,
        )

    if method_key == UNIT_TEST_RESOURCES_READ_METHOD:
        first = await manager.read_resource(
            UNIT_TEST_PROJECTS_URI,
            preferred=["primary", "backup"],
        )
    else:
        first = await manager.invoke_tool(
            UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["primary", "backup"]
        )
    assert first.server == UNIT_TEST_PRIMARY_SERVER

    if method_key == UNIT_TEST_INITIALIZE_METHOD:
        invalidated = await manager.invalidate_adapter_session(UNIT_TEST_PRIMARY_SERVER)
        assert invalidated is True

    if method_key == UNIT_TEST_RESOURCES_READ_METHOD:
        second = await manager.read_resource(
            UNIT_TEST_PROJECTS_URI,
            preferred=["primary", "backup"],
        )
    else:
        second = await manager.invoke_tool(
            UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["primary", "backup"]
        )
    assert second.server == UNIT_TEST_BACKUP_SERVER
    assert second.method == expected_method

    primary_events = manager.list_invocation_events(
        server=UNIT_TEST_PRIMARY_SERVER,
        method=expected_method,
        request_id=second.request_id,
    )
    if method_key == UNIT_TEST_INITIALIZE_METHOD:
        assert [event.phase for event in primary_events] == list(
            UNIT_TEST_INITIALIZE_START_FAILURE_PHASES
        )
        assert primary_events[1].error_category == UNIT_TEST_TIMEOUT_ERROR_CATEGORY
    else:
        assert [event.phase for event in primary_events] == [
            UNIT_TEST_INITIALIZE_START_PHASE,
            UNIT_TEST_INITIALIZE_SUCCESS_PHASE,
            UNIT_TEST_INVOKE_START_PHASE,
            UNIT_TEST_INVOKE_FAILURE_PHASE,
        ]
        assert primary_events[3].error_category == UNIT_TEST_TIMEOUT_ERROR_CATEGORY

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)

    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_TOOLS_CALL_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_VECTOR,
    )
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_BACKUP_SERVER,
        UNIT_TEST_RESOURCES_READ_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_VECTOR,
    )

    first = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME,
        preferred=["primary", "backup"],
    )
    assert first.server == UNIT_TEST_BACKUP_SERVER
    clock.advance(seconds=1)

    second = await manager.read_resource(
        UNIT_TEST_PROJECTS_URI,
        preferred=["backup", "primary"],
    )
    assert second.server == UNIT_TEST_PRIMARY_SERVER

    call_order = _unit_test_collect_mixed_method_call_order_slice(factory.calls, 0)
    assert call_order == list(UNIT_TEST_CLUSTER_NAT_MIXED_SCRIPTED_FAILOVER_CALL_ORDER)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", UNIT_TEST_CLUSTER_NAT_METHOD_VECTOR)
async def test_cluster_nat_repeated_invokes_skip_initialize_until_invalidate(
    method: str,
) -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)

    async def invoke_once() -> object:
        if method == UNIT_TEST_RESOURCES_READ_METHOD:
            return await manager.read_resource(UNIT_TEST_PROJECTS_URI, preferred=["primary"])
        return await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["primary"])

    first = await invoke_once()
    second = await invoke_once()
    assert first.server == UNIT_TEST_PRIMARY_SERVER
    assert second.server == UNIT_TEST_PRIMARY_SERVER
    assert first.method == method
    assert second.method == method

    expected_before_invalidate = {
        method_name: before_vector
        for method_name, before_vector, _ in UNIT_TEST_CLUSTER_NAT_REPEATED_INVOKES_PROGRESSIONS
    }[method]
    before_invalidate = _unit_test_collect_full_call_order_slice(factory.calls, 0, method)
    assert [call_method for _, _, call_method in before_invalidate] == list(
        expected_before_invalidate
    )
    assert before_invalidate[0][0] == UNIT_TEST_PRIMARY_SERVER
    assert before_invalidate[1][1] == before_invalidate[2][1]

    invalidated = await manager.invalidate_adapter_session(UNIT_TEST_PRIMARY_SERVER)
    assert invalidated is True

    third = await invoke_once()
    assert third.server == UNIT_TEST_PRIMARY_SERVER
    assert third.method == method

    expected_after_invalidate = {
        method_name: after_vector
        for method_name, _, after_vector in UNIT_TEST_CLUSTER_NAT_REPEATED_INVOKES_PROGRESSIONS
    }[method]
    call_order = _unit_test_collect_full_call_order_slice(factory.calls, 0, method)
    assert [call_method for _, _, call_method in call_order] == list(expected_after_invalidate)
    assert call_order[3][1] != call_order[2][1]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", UNIT_TEST_CLUSTER_NAT_METHOD_VECTOR)
@pytest.mark.parametrize("trigger", UNIT_TEST_CLUSTER_NAT_TRIGGER_VECTOR)
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)

    async def invoke_once() -> object:
        if method == UNIT_TEST_RESOURCES_READ_METHOD:
            return await manager.read_resource(UNIT_TEST_PROJECTS_URI, preferred=["primary"])
        return await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["primary"])

    first = await invoke_once()
    assert first.server == UNIT_TEST_PRIMARY_SERVER
    assert first.method == method

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
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

    expected_call_order = UNIT_TEST_CLUSTER_NAT_FORCE_REINITIALIZE_REENTRY_CALL_ORDER_LISTS[method]
    call_order = _unit_test_collect_reentry_call_order_slice(factory.calls, 0, method)
    assert call_order == expected_call_order


@pytest.mark.asyncio
@pytest.mark.parametrize("method", UNIT_TEST_CLUSTER_NAT_METHOD_VECTOR)
@pytest.mark.parametrize(
    ("unreachable_after", "expected_status"),
    UNIT_TEST_CLUSTER_NAT_UNREACHABLE_AFTER_STATUS_MATRIX,
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        method,
        UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_OK_VECTOR,
    )

    async def invoke_once() -> object:
        if method == UNIT_TEST_RESOURCES_READ_METHOD:
            return await manager.read_resource(
                UNIT_TEST_PROJECTS_URI,
                preferred=["primary", "backup"],
            )
        return await manager.invoke_tool(
            UNIT_TEST_PROJECT_LIST_TOOL_NAME,
            preferred=["primary", "backup"],
        )

    first = await invoke_once()
    assert first.server == UNIT_TEST_BACKUP_SERVER

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
    assert primary is not None
    assert primary.status is expected_status

    calls_after_first = len(factory.calls)
    second = await invoke_once()
    assert second.server == UNIT_TEST_BACKUP_SERVER

    second_slice = factory.calls[calls_after_first:]
    assert second_slice
    assert all(server == UNIT_TEST_BACKUP_SERVER for server, _, _ in second_slice)

    clock.advance(seconds=1)
    manager.record_check_result(
        UNIT_TEST_BACKUP_SERVER,
        healthy=False,
        error=UNIT_TEST_ERROR_HOLD_BACKUP,
    )

    calls_before_third = len(factory.calls)
    third = await invoke_once()
    assert third.server == UNIT_TEST_PRIMARY_SERVER
    assert third.method == method

    _assert_unit_test_collected_primary_reentry_slice(
        factory.calls,
        calls_before_third,
        method,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("backup_failures", "expected_backup_status"),
    UNIT_TEST_CLUSTER_NAT_FAILURE_COUNT_STATUS_MATRIX,
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_RESOURCES_READ_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_OK_VECTOR,
    )

    first = await manager.read_resource(
        UNIT_TEST_PROJECTS_URI,
        preferred=["primary", "backup"],
    )
    assert first.server == UNIT_TEST_BACKUP_SERVER

    second = await manager.read_resource(
        UNIT_TEST_PROJECTS_URI,
        preferred=["backup", "primary"],
    )
    assert second.server == UNIT_TEST_BACKUP_SERVER

    clock.advance(seconds=1)
    for _ in range(backup_failures):
        manager.record_check_result(
            UNIT_TEST_BACKUP_SERVER,
            healthy=False,
            error=UNIT_TEST_ERROR_HOLD_BACKUP,
        )
    backup = manager.get(UNIT_TEST_BACKUP_SERVER)
    assert backup is not None
    assert backup.status is expected_backup_status

    calls_before_third = len(factory.calls)
    third = await manager.read_resource(
        UNIT_TEST_PROJECTS_URI,
        preferred=["backup", "primary"],
    )
    assert third.server == UNIT_TEST_PRIMARY_SERVER

    third_slice = _unit_test_collect_reentry_call_order_slice(
        factory.calls,
        calls_before_third,
        UNIT_TEST_RESOURCES_READ_METHOD,
    )
    assert third_slice == list(UNIT_TEST_PRIMARY_RESOURCE_REENTRY_CALL_ORDER_SLICE)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", UNIT_TEST_CLUSTER_NAT_METHOD_VECTOR)
@pytest.mark.parametrize(
    ("primary_failures", "expected_primary_status"),
    UNIT_TEST_CLUSTER_NAT_FAILURE_COUNT_STATUS_MATRIX,
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        (
            UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_OK_VECTOR
            if primary_failures == 1
            else UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_TIMEOUT_OK_VECTOR
        ),
    )

    async def invoke_once(preferred: list[str]) -> object:
        if method == UNIT_TEST_RESOURCES_READ_METHOD:
            return await manager.read_resource(UNIT_TEST_PROJECTS_URI, preferred=preferred)
        return await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=preferred)

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
        manager.record_check_result(
            UNIT_TEST_BACKUP_SERVER,
            healthy=False,
            error=UNIT_TEST_ERROR_HOLD_BACKUP,
        )
        with pytest.raises(MCPInvocationError):
            await invoke_once(["primary"])
        primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
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

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
    assert primary is not None
    assert primary.status is expected_primary_status

    manager.record_check_result(
        UNIT_TEST_BACKUP_SERVER,
        healthy=False,
        error=UNIT_TEST_ERROR_HOLD_BACKUP,
    )

    calls_before_reentry = len(factory.calls)
    reentry = await invoke_once(["backup", "primary"])
    assert reentry.server == UNIT_TEST_PRIMARY_SERVER
    assert reentry.method == method

    _assert_unit_test_collected_primary_reentry_slice(
        factory.calls,
        calls_before_reentry,
        method,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method", UNIT_TEST_CLUSTER_NAT_METHOD_VECTOR)
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_TIMEOUT_OK_VECTOR,
    )

    async def invoke_once(preferred: list[str]) -> object:
        if method == UNIT_TEST_RESOURCES_READ_METHOD:
            return await manager.read_resource(UNIT_TEST_PROJECTS_URI, preferred=preferred)
        return await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=preferred)

    first = await invoke_once(["primary", "backup"])
    assert first.server == UNIT_TEST_BACKUP_SERVER

    clock.advance(seconds=1)
    manager.record_check_result(
        UNIT_TEST_BACKUP_SERVER,
        healthy=False,
        error=UNIT_TEST_ERROR_HOLD_BACKUP,
    )
    with pytest.raises(MCPInvocationError):
        await invoke_once(["primary"])

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
    assert primary is not None
    assert primary.status is ServerStatus.UNREACHABLE

    clock.advance(seconds=1)
    calls_before_backup_reentry = len(factory.calls)
    backup_reentry = await invoke_once(["primary", "backup"])
    assert backup_reentry.server == UNIT_TEST_BACKUP_SERVER
    assert backup_reentry.method == method

    _assert_unit_test_collected_backup_reentry_slice(
        factory.calls,
        calls_before_backup_reentry,
        method,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("backup_failures", "reopen_seconds", "expected_backup_status"),
    UNIT_TEST_CLUSTER_NAT_BACKUP_REOPEN_STATUS_MATRIX,
)
@pytest.mark.parametrize("method", UNIT_TEST_CLUSTER_NAT_METHOD_VECTOR)
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)
    _set_unit_test_failure_script(
        factory,
        UNIT_TEST_PRIMARY_SERVER,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_TIMEOUT_OK_VECTOR,
    )

    async def invoke_once(preferred: list[str]) -> object:
        if method == UNIT_TEST_RESOURCES_READ_METHOD:
            return await manager.read_resource(UNIT_TEST_PROJECTS_URI, preferred=preferred)
        return await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=preferred)

    first = await invoke_once(["primary", "backup"])
    assert first.server == UNIT_TEST_BACKUP_SERVER

    clock.advance(seconds=1)
    for _ in range(backup_failures):
        manager.record_check_result(
            UNIT_TEST_BACKUP_SERVER,
            healthy=False,
            error=UNIT_TEST_ERROR_HOLD_BACKUP,
        )
    backup = manager.get(UNIT_TEST_BACKUP_SERVER)
    assert backup is not None
    assert backup.status is expected_backup_status

    with pytest.raises(MCPInvocationError):
        await invoke_once(["primary"])
    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
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

    _assert_unit_test_collected_backup_reentry_slice(
        factory.calls,
        calls_before_reentry,
        method,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method", UNIT_TEST_CLUSTER_NAT_METHOD_VECTOR)
@pytest.mark.parametrize(
    ("preferred", "expected_first", "expected_second"),
    UNIT_TEST_CLUSTER_NAT_PREFERRED_REOPEN_MATRIX,
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)

    manager.record_check_result(
        UNIT_TEST_PRIMARY_SERVER,
        healthy=False,
        error=UNIT_TEST_ERROR_HOLD_PRIMARY,
    )
    manager.record_check_result(
        UNIT_TEST_BACKUP_SERVER,
        healthy=False,
        error=UNIT_TEST_ERROR_HOLD_BACKUP,
    )

    primary = manager.get(UNIT_TEST_PRIMARY_SERVER)
    backup = manager.get(UNIT_TEST_BACKUP_SERVER)
    assert primary is not None
    assert backup is not None
    assert primary.status is ServerStatus.UNREACHABLE
    assert backup.status is ServerStatus.UNREACHABLE

    _set_unit_test_failure_script(
        factory,
        expected_first,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_VECTOR,
    )
    _set_unit_test_failure_script(
        factory,
        expected_second,
        UNIT_TEST_INITIALIZE_METHOD,
        UNIT_TEST_FAILURE_SCRIPT_OK_VECTOR,
    )

    async def invoke_once() -> object:
        if method == UNIT_TEST_RESOURCES_READ_METHOD:
            return await manager.read_resource(UNIT_TEST_PROJECTS_URI, preferred=preferred)
        return await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=preferred)

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
    assert (
        initialize_starts
        == UNIT_TEST_CLUSTER_NAT_REOPEN_INITIALIZE_START_SERVER_ORDERS[tuple(preferred)]
    )

    reopen_slice = _unit_test_collect_reentry_call_order_slice(
        factory.calls,
        calls_before_reopen,
        method,
    )
    _assert_unit_test_reopen_slice(reopen_slice, expected_second, method)


@pytest.mark.asyncio
async def test_invocation_failure_records_correlation_id_on_connection_events() -> None:
    async def transport(server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        if method == UNIT_TEST_INITIALIZE_METHOD:
            raise RuntimeError(UNIT_TEST_ERROR_INIT_DOWN)
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {},
        }

    manager = MCPClientManager(transport=transport)
    manager.register("codex", UNIT_TEST_CODEX_SERVER_URL)

    with pytest.raises(MCPInvocationError):
        await manager.invoke_tool(UNIT_TEST_PROJECT_LIST_TOOL_NAME)

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
            raise RuntimeError(UNIT_TEST_ERROR_PRIMARY_UNAVAILABLE)
        if method == UNIT_TEST_INITIALIZE_METHOD:
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "result": {"protocolVersion": "2025-11-25"},
            }
        if method == UNIT_TEST_NOTIFICATIONS_INITIALIZED_METHOD:
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
    manager.register("primary", UNIT_TEST_PRIMARY_SERVER_URL)
    manager.register("backup", UNIT_TEST_BACKUP_SERVER_URL)

    result = await manager.invoke_tool(
        UNIT_TEST_PROJECT_LIST_TOOL_NAME, preferred=["primary", "backup"]
    )
    request_id = result.request_id
    manager.record_check_result(
        UNIT_TEST_BACKUP_SERVER,
        healthy=False,
        error=UNIT_TEST_ERROR_MANUAL_DEGRADE,
    )

    primary_invocation = manager.list_invocation_events(
        server=UNIT_TEST_PRIMARY_SERVER,
        request_id=request_id,
    )
    assert [event.phase for event in primary_invocation] == list(
        UNIT_TEST_INITIALIZE_START_FAILURE_PHASES
    )

    latest_invocation = manager.list_invocation_events(limit=2)
    assert [event.phase for event in latest_invocation] == list(
        UNIT_TEST_INVOKE_START_SUCCESS_PHASES
    )

    correlated_connection = manager.list_events(correlation_id=request_id)
    assert len(correlated_connection) == 1
    assert correlated_connection[0].server == UNIT_TEST_PRIMARY_SERVER

    backup_connection = manager.list_events(server=UNIT_TEST_BACKUP_SERVER)
    assert len(backup_connection) == 1
    assert backup_connection[0].correlation_id is None

    latest_connection = manager.list_events(limit=1)
    assert len(latest_connection) == 1
    assert latest_connection[0].server == UNIT_TEST_BACKUP_SERVER
