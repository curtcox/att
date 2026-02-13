from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import get_mcp_client_manager
from att.mcp.client import (
    ExternalServer,
    JSONObject,
    MCPClientManager,
    MCPTransportError,
    NATMCPTransportAdapter,
    ServerStatus,
)
from tests.support.mcp_convergence_helpers import (
    assert_call_order_subsequence,
    assert_connection_event_filters,
    assert_invocation_event_filters,
    collect_invocation_events_for_requests,
    expected_call_order_from_phase_starts,
    expected_phases_for_server,
    extract_request_id_from_invocation_event_delta,
)
from tests.support.mcp_helpers import MCPTestClock
from tests.support.mcp_nat_helpers import APIFakeNatSessionFactory, ClusterNatSessionFactory


class StaticProbe:
    def __init__(self, healthy: bool, error: str | None = None) -> None:
        self._healthy = healthy
        self._error = error

    async def __call__(self, _: ExternalServer) -> tuple[bool, str | None]:
        return self._healthy, self._error


class FallbackTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def __call__(self, server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        self.calls.append((server.name, method))
        if server.name == "codex":
            raise RuntimeError("codex unavailable")
        if server.name == "failing":
            return {
                "jsonrpc": "2.0",
                "id": str(request.get("id", "")),
                "error": {"message": "rpc failure"},
            }
        return {
            "jsonrpc": "2.0",
            "id": str(request.get("id", "")),
            "result": {"served_by": server.name, "method": str(request.get("method", ""))},
        }


class RecoveringTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def __call__(self, server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        self.calls.append((server.name, method))
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
            "result": {"served_by": server.name, "method": str(request.get("method", ""))},
        }


class CategorizedTransport:
    def __init__(self, *, invoke_failure: str) -> None:
        self.invoke_failure = invoke_failure
        self.calls: list[tuple[str, str]] = []

    async def __call__(self, server: ExternalServer, request: JSONObject) -> JSONObject:
        method = str(request.get("method", ""))
        self.calls.append((server.name, method))
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
        if self.invoke_failure == "http_status":
            raise MCPTransportError("http status 503", category="http_status")
        return {"jsonrpc": "2.0", "id": str(request.get("id", ""))}


class ShouldNotBeCalledTransport:
    async def __call__(self, server: ExternalServer, request: JSONObject) -> JSONObject:
        del server, request
        msg = "legacy transport path should not be used when adapter is configured"
        raise AssertionError(msg)


def _client_with_manager(manager: MCPClientManager) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_mcp_client_manager] = lambda: manager
    return TestClient(app)


@dataclass(frozen=True)
class UnreachableTransitionSequence:
    request_id_1: str
    request_id_2: str
    request_id_3: str
    request_id_4: str
    request_id_5: str
    calls_after_first: int
    calls_after_third: int
    calls_before_fifth: int


@dataclass(frozen=True)
class RetryWindowHarness:
    factory: ClusterNatSessionFactory
    clock: MCPTestClock
    manager: MCPClientManager
    client: TestClient


@dataclass(frozen=True)
class RetryWindowGatingSequence:
    request_id_1: str
    request_id_2: str
    request_id_3: str
    calls_after_first: int
    calls_before_third: int


@dataclass(frozen=True)
class SimultaneousUnreachableReopenSequence:
    request_id: str
    method: str
    calls_before_reopen: int


PRIMARY_UNREACHABLE_TRANSITION_EXPECTED_PHASES: tuple[list[str], ...] = (
    ["initialize_start", "initialize_failure"],
    [],
    ["initialize_start", "initialize_failure"],
    [],
    ["initialize_start", "initialize_success", "invoke_start", "invoke_success"],
)
PRIMARY_UNREACHABLE_TRANSITION_EXPECTED_STATUSES: tuple[list[str], ...] = (
    [ServerStatus.DEGRADED.value],
    [],
    [ServerStatus.UNREACHABLE.value],
    [],
    [ServerStatus.HEALTHY.value],
)
PRIMARY_RETRY_WINDOW_GATING_EXPECTED_PHASES: tuple[list[str], ...] = (
    ["initialize_start", "initialize_success", "invoke_start", "invoke_failure"],
    [],
    ["initialize_start", "initialize_success", "invoke_start", "invoke_success"],
)
PRIMARY_RETRY_WINDOW_GATING_EXPECTED_STATUSES: tuple[list[str], ...] = (
    [ServerStatus.DEGRADED.value],
    [],
    [ServerStatus.HEALTHY.value],
)
RETRY_WINDOW_GATING_TOOL_EXPECTED_THIRD_SLICE: tuple[tuple[str, str], ...] = (
    ("primary", "initialize"),
    ("primary", "tools/call"),
)
RETRY_WINDOW_GATING_TOOL_EXPECTED_OBSERVED_CALL_ORDER: tuple[tuple[str, str], ...] = (
    ("primary", "initialize"),
    ("primary", "tools/call"),
    ("backup", "initialize"),
    ("backup", "tools/call"),
    ("backup", "tools/call"),
    ("primary", "initialize"),
    ("primary", "tools/call"),
)
RETRY_WINDOW_GATING_RESOURCE_EXPECTED_THIRD_SLICE: tuple[tuple[str, str], ...] = (
    ("primary", "initialize"),
    ("primary", "resources/read"),
)
RETRY_WINDOW_GATING_RESOURCE_EXPECTED_OBSERVED_CALL_ORDER: tuple[tuple[str, str], ...] = (
    ("primary", "initialize"),
    ("primary", "resources/read"),
    ("backup", "initialize"),
    ("backup", "resources/read"),
    ("backup", "resources/read"),
    ("primary", "initialize"),
    ("primary", "resources/read"),
)
UNREACHABLE_TRANSITION_TOOL_EXPECTED_FIFTH_SLICE: tuple[tuple[str, str], ...] = (
    ("primary", "initialize"),
    ("primary", "tools/call"),
)
UNREACHABLE_TRANSITION_TOOL_EXPECTED_OBSERVED_CALL_ORDER: tuple[tuple[str, str], ...] = (
    ("backup", "initialize"),
    ("backup", "tools/call"),
    ("backup", "tools/call"),
    ("backup", "initialize"),
    ("backup", "tools/call"),
    ("primary", "initialize"),
    ("primary", "tools/call"),
)
UNREACHABLE_TRANSITION_RESOURCE_EXPECTED_FIFTH_SLICE: tuple[tuple[str, str], ...] = (
    ("primary", "initialize"),
    ("primary", "resources/read"),
)
UNREACHABLE_TRANSITION_RESOURCE_EXPECTED_OBSERVED_CALL_ORDER: tuple[tuple[str, str], ...] = (
    ("backup", "initialize"),
    ("backup", "resources/read"),
    ("backup", "resources/read"),
    ("backup", "initialize"),
    ("backup", "resources/read"),
    ("primary", "initialize"),
    ("primary", "resources/read"),
)


def _create_retry_window_harness(*, unreachable_after: int) -> RetryWindowHarness:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=unreachable_after,
    )
    client = _client_with_manager(manager)
    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})
    return RetryWindowHarness(
        factory=factory,
        clock=clock,
        manager=manager,
        client=client,
    )


def _build_invoke_with_preferred(
    client: TestClient,
    *,
    invoke_path: str,
    payload: dict[str, object],
) -> Callable[[list[str]], Any]:
    def invoke(preferred_servers: list[str]) -> Any:
        return client.post(
            invoke_path,
            json={**payload, "preferred_servers": preferred_servers},
        )

    return invoke


def _run_retry_window_gating_sequence(
    *,
    invoke: Callable[[list[str]], Any],
    manager: MCPClientManager,
    clock: MCPTestClock,
    factory: ClusterNatSessionFactory,
    third_preferred: list[str],
) -> RetryWindowGatingSequence:
    first = invoke(["primary", "backup"])
    assert first.status_code == 200
    assert first.json()["server"] == "backup"
    request_id_1 = first.json()["request_id"]

    calls_after_first = len(factory.calls)
    second = invoke(["primary", "backup"])
    assert second.status_code == 200
    assert second.json()["server"] == "backup"
    request_id_2 = second.json()["request_id"]
    second_slice = factory.calls[calls_after_first:]
    assert second_slice
    assert all(server == "backup" for server, _, _ in second_slice)

    clock.advance(seconds=1)
    manager.record_check_result("backup", healthy=False, error="hold backup")

    calls_before_third = len(factory.calls)
    third = invoke(third_preferred)
    assert third.status_code == 200
    assert third.json()["server"] == "primary"
    request_id_3 = third.json()["request_id"]

    return RetryWindowGatingSequence(
        request_id_1=request_id_1,
        request_id_2=request_id_2,
        request_id_3=request_id_3,
        calls_after_first=calls_after_first,
        calls_before_third=calls_before_third,
    )


def _run_unreachable_transition_sequence(
    *,
    invoke: Callable[[list[str]], Any],
    client: TestClient,
    manager: MCPClientManager,
    clock: MCPTestClock,
    factory: ClusterNatSessionFactory,
) -> UnreachableTransitionSequence:
    first = invoke(["primary", "backup"])
    assert first.status_code == 200
    assert first.json()["server"] == "backup"
    request_id_1 = first.json()["request_id"]

    calls_after_first = len(factory.calls)
    second = invoke(["primary", "backup"])
    assert second.status_code == 200
    assert second.json()["server"] == "backup"
    request_id_2 = second.json()["request_id"]
    second_slice = factory.calls[calls_after_first:]
    assert second_slice
    assert all(server == "backup" for server, _, _ in second_slice)

    clock.advance(seconds=1)
    manager.record_check_result("backup", healthy=False, error="hold backup")
    invocation_count_before_third = len(client.get("/api/v1/mcp/invocation-events").json()["items"])
    third = invoke(["primary"])
    assert third.status_code == 503
    request_id_3 = extract_request_id_from_invocation_event_delta(
        client,
        previous_count=invocation_count_before_third,
        expected_phases=[
            "initialize_start",
            "initialize_failure",
        ],
    )

    primary_after_third = client.get("/api/v1/mcp/servers/primary")
    assert primary_after_third.status_code == 200
    assert primary_after_third.json()["status"] == ServerStatus.UNREACHABLE.value
    assert primary_after_third.json()["retry_count"] == 2

    clock.advance(seconds=1)
    calls_after_third = len(factory.calls)
    fourth = invoke(["primary", "backup"])
    assert fourth.status_code == 200
    assert fourth.json()["server"] == "backup"
    request_id_4 = fourth.json()["request_id"]
    fourth_slice = factory.calls[calls_after_third:]
    assert fourth_slice
    assert all(server == "backup" for server, _, _ in fourth_slice)

    clock.advance(seconds=2)
    manager.record_check_result("backup", healthy=False, error="hold backup")

    calls_before_fifth = len(factory.calls)
    fifth = invoke(["backup", "primary"])
    assert fifth.status_code == 200
    assert fifth.json()["server"] == "primary"
    request_id_5 = fifth.json()["request_id"]

    return UnreachableTransitionSequence(
        request_id_1=request_id_1,
        request_id_2=request_id_2,
        request_id_3=request_id_3,
        request_id_4=request_id_4,
        request_id_5=request_id_5,
        calls_after_first=calls_after_first,
        calls_after_third=calls_after_third,
        calls_before_fifth=calls_before_fifth,
    )


def _retry_window_request_ids(sequence: RetryWindowGatingSequence) -> tuple[str, str, str]:
    return (
        sequence.request_id_1,
        sequence.request_id_2,
        sequence.request_id_3,
    )


def _unreachable_transition_request_ids(
    sequence: UnreachableTransitionSequence,
) -> tuple[str, str, str, str, str]:
    return (
        sequence.request_id_1,
        sequence.request_id_2,
        sequence.request_id_3,
        sequence.request_id_4,
        sequence.request_id_5,
    )


def _assert_primary_request_diagnostics(
    *,
    client: TestClient,
    method: str,
    request_ids: Sequence[str],
    expected_phases: Sequence[list[str]],
    expected_statuses: Sequence[list[str]],
) -> None:
    assert len(request_ids) == len(expected_phases) == len(expected_statuses)
    for request_id, phases, statuses in zip(
        request_ids,
        expected_phases,
        expected_statuses,
        strict=True,
    ):
        assert_invocation_event_filters(
            client,
            request_id=request_id,
            server="primary",
            method=method,
            expected_phases=phases,
        )
        assert_connection_event_filters(
            client,
            request_id=request_id,
            server="primary",
            expected_statuses=statuses,
        )


def _collect_method_call_order(
    *,
    factory: ClusterNatSessionFactory,
    method: str,
    start_index: int = 0,
) -> list[tuple[str, str]]:
    relevant_methods = {"initialize", method}
    return [
        (server, call_method)
        for server, _, call_method in factory.calls[start_index:]
        if call_method in relevant_methods
    ]


def _collect_mixed_method_call_order(
    *,
    factory: ClusterNatSessionFactory,
) -> list[tuple[str, str]]:
    return [
        (server, method)
        for server, _, method in factory.calls
        if method in {"initialize", "tools/call", "resources/read"}
    ]


def _expected_call_order_for_requests(
    *,
    client: TestClient,
    request_ids: Sequence[str],
) -> list[tuple[str, str]]:
    events = collect_invocation_events_for_requests(client, request_ids=request_ids)
    return expected_call_order_from_phase_starts(events)


def _assert_unreachable_transition_call_order_literals(
    *,
    factory: ClusterNatSessionFactory,
    sequence: UnreachableTransitionSequence,
    method: str,
    expected_fifth_slice: Sequence[tuple[str, str]],
    expected_observed_call_order: Sequence[tuple[str, str]],
) -> list[tuple[str, str]]:
    fifth_slice = _collect_method_call_order(
        factory=factory,
        method=method,
        start_index=sequence.calls_before_fifth,
    )
    assert fifth_slice == list(expected_fifth_slice)

    observed_call_order = _collect_method_call_order(factory=factory, method=method)
    assert observed_call_order == list(expected_observed_call_order)
    return observed_call_order


def _assert_retry_window_gating_call_order_literals(
    *,
    factory: ClusterNatSessionFactory,
    sequence: RetryWindowGatingSequence,
    method: str,
    expected_third_slice: Sequence[tuple[str, str]],
    expected_observed_call_order: Sequence[tuple[str, str]],
) -> list[tuple[str, str]]:
    second_slice = factory.calls[sequence.calls_after_first : sequence.calls_before_third]
    assert second_slice
    assert all(server == "backup" for server, _, _ in second_slice)

    third_slice = _collect_method_call_order(
        factory=factory,
        method=method,
        start_index=sequence.calls_before_third,
    )
    assert third_slice == list(expected_third_slice)

    observed_call_order = _collect_method_call_order(factory=factory, method=method)
    assert observed_call_order == list(expected_observed_call_order)
    return observed_call_order


def _run_simultaneous_unreachable_reopen_sequence(
    *,
    invoke: Callable[[list[str]], Any],
    client: TestClient,
    manager: MCPClientManager,
    clock: MCPTestClock,
    factory: ClusterNatSessionFactory,
    preferred: list[str],
    expected_first: str,
    expected_second: str,
) -> SimultaneousUnreachableReopenSequence:
    manager.record_check_result("primary", healthy=False, error="hold primary")
    manager.record_check_result("backup", healthy=False, error="hold backup")
    primary = manager.get("primary")
    backup = manager.get("backup")
    assert primary is not None
    assert backup is not None
    assert primary.status is ServerStatus.UNREACHABLE
    assert backup.status is ServerStatus.UNREACHABLE

    calls_before_closed = len(factory.calls)
    invocation_count_before_closed = len(
        client.get("/api/v1/mcp/invocation-events").json()["items"]
    )
    closed = invoke(preferred)
    assert closed.status_code == 503
    assert closed.json()["detail"]["message"] == "No reachable MCP servers are currently available"
    invocation_count_after_closed = len(client.get("/api/v1/mcp/invocation-events").json()["items"])
    assert invocation_count_after_closed == invocation_count_before_closed
    assert len(factory.calls) == calls_before_closed

    factory.set_failure_script(expected_first, "initialize", ["timeout"])
    factory.set_failure_script(expected_second, "initialize", ["ok"])
    clock.advance(seconds=1)

    calls_before_reopen = len(factory.calls)
    reopened = invoke(preferred)
    assert reopened.status_code == 200
    assert reopened.json()["server"] == expected_second

    return SimultaneousUnreachableReopenSequence(
        request_id=reopened.json()["request_id"],
        method=reopened.json()["method"],
        calls_before_reopen=calls_before_reopen,
    )


def test_mcp_catalog_endpoints() -> None:
    client = _client_with_manager(MCPClientManager())

    tools = client.get("/api/v1/mcp/tools")
    assert tools.status_code == 200
    tool_names = {item["name"] for item in tools.json()}
    assert "att.project.create" in tool_names
    assert "att.runtime.status" in tool_names

    resources = client.get("/api/v1/mcp/resources")
    assert resources.status_code == 200
    uris = {item["uri"] for item in resources.json()}
    assert "att://projects" in uris
    assert "att://project/{id}/ci" in uris


def test_mcp_server_register_list_and_health_check_healthy() -> None:
    manager = MCPClientManager(probe=StaticProbe(healthy=True))
    client = _client_with_manager(manager)

    create = client.post(
        "/api/v1/mcp/servers",
        json={"name": "codex", "url": "http://codex.local"},
    )
    assert create.status_code == 201
    assert create.json()["status"] == ServerStatus.HEALTHY.value
    assert create.json()["initialized"] is False

    listing = client.get("/api/v1/mcp/servers")
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1

    fetched = client.get("/api/v1/mcp/servers/codex")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "codex"

    checked = client.post("/api/v1/mcp/servers/codex/health-check")
    assert checked.status_code == 200
    assert checked.json()["status"] == ServerStatus.HEALTHY.value


def test_mcp_server_initialize_endpoints() -> None:
    transport = FallbackTransport()
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "codex", "url": "http://codex.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "github", "url": "http://github.local"},
    )

    one = client.post("/api/v1/mcp/servers/github/initialize")
    assert one.status_code == 200
    assert one.json()["initialized"] is True
    assert one.json()["capability_snapshot"] is not None
    assert one.json()["capability_snapshot"]["protocol_version"] is None
    assert one.json()["capability_snapshot"]["server_info"] is None
    assert one.json()["capability_snapshot"]["capabilities"] is None

    all_servers = client.post("/api/v1/mcp/servers/initialize")
    assert all_servers.status_code == 200
    assert len(all_servers.json()["items"]) == 2
    by_name = {item["name"]: item for item in all_servers.json()["items"]}
    assert by_name["github"]["initialized"] is True
    assert by_name["github"]["capability_snapshot"] is not None
    assert by_name["codex"]["initialized"] is False
    assert by_name["codex"]["status"] in {
        ServerStatus.DEGRADED.value,
        ServerStatus.UNREACHABLE.value,
    }


def test_mcp_server_connect_endpoints() -> None:
    transport = FallbackTransport()
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "codex", "url": "http://codex.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "github", "url": "http://github.local"},
    )

    one = client.post("/api/v1/mcp/servers/github/connect")
    assert one.status_code == 200
    assert one.json()["initialized"] is True
    assert one.json()["status"] == ServerStatus.HEALTHY.value
    assert one.json()["capability_snapshot"] is not None

    failing = client.post("/api/v1/mcp/servers/codex/connect")
    assert failing.status_code == 200
    assert failing.json()["initialized"] is False
    assert failing.json()["status"] in {
        ServerStatus.DEGRADED.value,
        ServerStatus.UNREACHABLE.value,
    }

    all_servers = client.post("/api/v1/mcp/servers/connect")
    assert all_servers.status_code == 200
    assert len(all_servers.json()["items"]) == 2


def test_mcp_server_health_check_degraded_and_missing() -> None:
    manager = MCPClientManager(probe=StaticProbe(healthy=False, error="timeout"))
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "github", "url": "http://github.local"},
    )
    checked = client.post("/api/v1/mcp/servers/github/health-check")
    assert checked.status_code == 200
    assert checked.json()["status"] == ServerStatus.DEGRADED.value
    assert checked.json()["last_error"] == "timeout"
    assert checked.json()["last_error_category"] == "health_check"

    events = client.get("/api/v1/mcp/events")
    assert events.status_code == 200
    assert len(events.json()["items"]) == 1
    assert events.json()["items"][0]["to_status"] == ServerStatus.DEGRADED.value

    missing = client.post("/api/v1/mcp/servers/missing/health-check")
    assert missing.status_code == 404

    missing_get = client.get("/api/v1/mcp/servers/missing")
    assert missing_get.status_code == 404


def test_mcp_check_all_servers_endpoint() -> None:
    manager = MCPClientManager(probe=StaticProbe(healthy=True))
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "codex", "url": "http://codex.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "github", "url": "http://github.local"},
    )
    checked = client.post("/api/v1/mcp/servers/health-check")
    assert checked.status_code == 200
    names = {item["name"] for item in checked.json()["items"]}
    assert names == {"codex", "github"}

    deleted = client.delete("/api/v1/mcp/servers/codex")
    assert deleted.status_code == 204

    deleted_missing = client.delete("/api/v1/mcp/servers/codex")
    assert deleted_missing.status_code == 404


def test_mcp_invoke_tool_with_fallback() -> None:
    transport = FallbackTransport()
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "codex", "url": "http://codex.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "github", "url": "http://github.local"},
    )

    invoke = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {"limit": 5},
            "preferred_servers": ["codex", "github"],
        },
    )
    assert invoke.status_code == 200
    payload = invoke.json()
    assert payload["server"] == "github"
    assert payload["method"] == "tools/call"
    assert payload["result"]["served_by"] == "github"
    assert transport.calls[0] == ("codex", "initialize")
    assert ("github", "initialize") in transport.calls
    assert ("github", "notifications/initialized") in transport.calls
    assert transport.calls[-1] == ("github", "tools/call")

    servers = client.get("/api/v1/mcp/servers")
    statuses = {item["name"]: item["status"] for item in servers.json()["items"]}
    initialized = {item["name"]: item["initialized"] for item in servers.json()["items"]}
    assert statuses["codex"] == ServerStatus.DEGRADED.value
    assert statuses["github"] == ServerStatus.HEALTHY.value
    assert initialized["codex"] is False
    assert initialized["github"] is True

    invocation_events = client.get("/api/v1/mcp/invocation-events")
    assert invocation_events.status_code == 200
    items = invocation_events.json()["items"]
    assert [item["phase"] for item in items] == [
        "initialize_start",
        "initialize_failure",
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in items] == [
        "codex",
        "codex",
        "github",
        "github",
        "github",
        "github",
    ]
    assert items[1]["error_category"] == "transport_error"
    assert items[1]["error"] == "codex unavailable"
    assert items[5]["error"] is None


def test_mcp_invoke_resource_and_error_when_unavailable() -> None:
    transport = FallbackTransport()
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "failing", "url": "http://failing.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "backup", "url": "http://backup.local"},
    )

    resource = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["failing", "backup"],
        },
    )
    assert resource.status_code == 200
    assert resource.json()["server"] == "backup"
    assert resource.json()["method"] == "resources/read"
    assert ("backup", "initialize") in transport.calls
    assert ("backup", "resources/read") in transport.calls

    empty_client = _client_with_manager(MCPClientManager())
    unavailable = empty_client.post(
        "/api/v1/mcp/invoke/tool",
        json={"tool_name": "att.project.list", "arguments": {}},
    )
    assert unavailable.status_code == 503
    unavailable_detail = unavailable.json()["detail"]
    assert unavailable_detail["method"] == "tools/call"
    assert unavailable_detail["attempts"] == []
    assert "No reachable MCP servers" in unavailable_detail["message"]


def test_mcp_invoke_error_payload_includes_attempt_trace() -> None:
    transport = FallbackTransport()
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "failing", "url": "http://failing.local"},
    )

    failed = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["failing"],
        },
    )
    assert failed.status_code == 503
    detail = failed.json()["detail"]
    assert detail["method"] == "resources/read"
    assert len(detail["attempts"]) == 1
    assert detail["attempts"][0]["server"] == "failing"
    assert detail["attempts"][0]["stage"] == "initialize"
    assert detail["attempts"][0]["success"] is False
    assert detail["attempts"][0]["error"] == "rpc error: rpc failure"
    assert detail["attempts"][0]["error_category"] == "rpc_error"


def test_mcp_invoke_tool_reinitializes_stale_server_before_call() -> None:
    transport = RecoveringTransport()
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "github", "url": "http://github.local"},
    )
    initialized = client.post("/api/v1/mcp/servers/github/initialize")
    assert initialized.status_code == 200

    server = manager.get("github")
    assert server is not None
    server.initialization_expires_at = datetime.now(UTC) - timedelta(seconds=1)

    invoke = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {"limit": 1},
            "preferred_servers": ["github"],
        },
    )
    assert invoke.status_code == 200
    assert invoke.json()["server"] == "github"
    assert transport.calls.count(("github", "initialize")) == 2
    assert transport.calls[-1] == ("github", "tools/call")

    fetched = client.get("/api/v1/mcp/servers/github")
    assert fetched.status_code == 200
    assert fetched.json()["initialization_expires_at"] is not None


def test_mcp_invoke_mixed_state_cluster_recovers_in_order() -> None:
    transport = RecoveringTransport()
    clock = MCPTestClock()
    manager = MCPClientManager(
        probe=StaticProbe(healthy=True),
        transport=transport,
        now_provider=clock,
    )
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "primary", "url": "http://primary.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "recovered", "url": "http://recovered.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "degraded", "url": "http://degraded.local"},
    )

    primary = manager.get("primary")
    assert primary is not None
    primary.status = ServerStatus.HEALTHY
    primary.initialized = True
    primary.last_initialized_at = clock.current
    primary.initialization_expires_at = clock.current + timedelta(seconds=120)

    recovered = manager.get("recovered")
    assert recovered is not None
    recovered.status = ServerStatus.HEALTHY
    recovered.initialized = False

    manager.record_check_result("degraded", healthy=False, error="down")
    clock.advance(seconds=2)

    invoke = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "recovered", "degraded"],
        },
    )
    assert invoke.status_code == 200
    assert invoke.json()["server"] == "recovered"
    assert transport.calls[0] == ("primary", "tools/call")
    assert transport.calls[1] == ("recovered", "initialize")
    assert transport.calls[2] == ("recovered", "notifications/initialized")
    assert transport.calls[3] == ("recovered", "tools/call")
    assert ("degraded", "initialize") not in transport.calls

    servers = client.get("/api/v1/mcp/servers")
    assert servers.status_code == 200
    by_name = {item["name"]: item for item in servers.json()["items"]}
    assert by_name["primary"]["status"] == ServerStatus.DEGRADED.value
    assert by_name["primary"]["last_error_category"] == "rpc_error"
    assert by_name["recovered"]["status"] == ServerStatus.HEALTHY.value
    assert by_name["recovered"]["initialized"] is True


def test_mcp_invoke_error_payload_http_status_category() -> None:
    transport = CategorizedTransport(invoke_failure="http_status")
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "httpfail", "url": "http://httpfail.local"},
    )
    failed = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["httpfail"],
        },
    )
    assert failed.status_code == 503
    detail = failed.json()["detail"]
    assert detail["method"] == "tools/call"
    assert len(detail["attempts"]) == 2
    assert detail["attempts"][1]["stage"] == "invoke"
    assert detail["attempts"][1]["error_category"] == "http_status"

    server = client.get("/api/v1/mcp/servers/httpfail")
    assert server.status_code == 200
    assert server.json()["last_error_category"] == "http_status"


def test_mcp_invoke_error_payload_malformed_category() -> None:
    transport = CategorizedTransport(invoke_failure="invalid_payload")
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "malformed", "url": "http://malformed.local"},
    )
    failed = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["malformed"],
        },
    )
    assert failed.status_code == 503
    detail = failed.json()["detail"]
    assert detail["method"] == "resources/read"
    assert len(detail["attempts"]) == 2
    assert detail["attempts"][1]["stage"] == "invoke"
    assert detail["attempts"][1]["error_category"] == "invalid_payload"

    server = client.get("/api/v1/mcp/servers/malformed")
    assert server.status_code == 200
    assert server.json()["last_error_category"] == "invalid_payload"


def test_mcp_event_endpoints_support_filters_limits_and_correlation() -> None:
    transport = FallbackTransport()
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "codex", "url": "http://codex.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "github", "url": "http://github.local"},
    )

    invoke = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["codex", "github"],
        },
    )
    assert invoke.status_code == 200
    request_id = invoke.json()["request_id"]

    manager.record_check_result("github", healthy=False, error="manual degrade")

    assert_invocation_event_filters(
        client,
        request_id=request_id,
        server="codex",
        method="tools/call",
        expected_phases=[
            "initialize_start",
            "initialize_failure",
        ],
    )

    invocation_limited = client.get("/api/v1/mcp/invocation-events", params={"limit": 2})
    assert invocation_limited.status_code == 200
    limited_invocation_items = invocation_limited.json()["items"]
    assert [item["phase"] for item in limited_invocation_items] == [
        "invoke_start",
        "invoke_success",
    ]

    assert_connection_event_filters(
        client,
        request_id=request_id,
        server="codex",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )
    correlated_connection = client.get("/api/v1/mcp/events", params={"correlation_id": request_id})
    assert correlated_connection.status_code == 200
    correlated_items = correlated_connection.json()["items"]
    assert len(correlated_items) == 1
    assert correlated_items[0]["correlation_id"] == request_id

    github_connection = client.get("/api/v1/mcp/events", params={"server": "github"})
    assert github_connection.status_code == 200
    github_items = github_connection.json()["items"]
    assert len(github_items) == 1
    assert github_items[0]["server"] == "github"
    assert github_items[0]["correlation_id"] is None

    limited_connection = client.get("/api/v1/mcp/events", params={"limit": 1})
    assert limited_connection.status_code == 200
    limited_connection_items = limited_connection.json()["items"]
    assert len(limited_connection_items) == 1
    assert limited_connection_items[0]["server"] == "github"


def test_mcp_resource_failover_recovery_filters_and_correlation() -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=2,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    warm_backup = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert warm_backup.status_code == 200
    assert warm_backup.json()["server"] == "backup"
    assert warm_backup.json()["method"] == "resources/read"

    factory.fail_on_timeout_initialize.add("primary")
    first_failover = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first_failover.status_code == 200
    assert first_failover.json()["server"] == "backup"
    assert first_failover.json()["method"] == "resources/read"
    request_id_1 = first_failover.json()["request_id"]

    assert_invocation_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        method="resources/read",
        expected_phases=["initialize_start", "initialize_failure"],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    during_window = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert during_window.status_code == 200
    assert during_window.json()["server"] == "backup"
    request_id_2 = during_window.json()["request_id"]

    assert_invocation_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        method="resources/read",
        expected_phases=[],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        expected_statuses=[],
    )

    factory.fail_on_timeout_initialize.remove("primary")
    clock.advance(seconds=1)
    manager.record_check_result("backup", healthy=False, error="hold backup")

    recovery = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert recovery.status_code == 200
    assert recovery.json()["server"] == "primary"
    assert recovery.json()["method"] == "resources/read"
    request_id_3 = recovery.json()["request_id"]

    assert_invocation_event_filters(
        client,
        request_id=request_id_3,
        server="primary",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_3,
        server="primary",
        expected_statuses=[ServerStatus.HEALTHY.value],
    )

    primary = client.get("/api/v1/mcp/servers/primary")
    assert primary.status_code == 200
    assert primary.json()["status"] == ServerStatus.HEALTHY.value


def test_mcp_invoke_uses_adapter_transport_when_configured() -> None:
    adapter = FallbackTransport()
    manager = MCPClientManager(
        probe=StaticProbe(healthy=True),
        transport=ShouldNotBeCalledTransport(),
        transport_adapter=adapter,
    )
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "codex", "url": "http://codex.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "github", "url": "http://github.local"},
    )

    invoke = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {"limit": 2},
            "preferred_servers": ["codex", "github"],
        },
    )
    assert invoke.status_code == 200
    assert invoke.json()["server"] == "github"
    assert adapter.calls[0] == ("codex", "initialize")
    assert adapter.calls[-1] == ("github", "tools/call")


def test_mcp_adapter_session_lifecycle_and_diagnostics_endpoints() -> None:
    factory = APIFakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "nat", "url": "http://nat.local"},
    )

    listing = client.get("/api/v1/mcp/servers")
    assert listing.status_code == 200
    assert listing.json()["adapter_controls_available"] is True
    assert listing.json()["items"][0]["adapter_controls_available"] is True

    before = client.get("/api/v1/mcp/servers/nat")
    assert before.status_code == 200
    assert before.json()["adapter_controls_available"] is True
    assert before.json()["adapter_session"]["active"] is False
    assert before.json()["adapter_session"]["initialized"] is False
    assert before.json()["adapter_session"]["last_activity_at"] is None
    assert before.json()["adapter_session"]["freshness"] == "unknown"

    invoke_before_refresh = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["nat"],
        },
    )
    assert invoke_before_refresh.status_code == 200
    session_id_before_refresh = invoke_before_refresh.json()["result"]["structuredContent"][
        "session_id"
    ]

    after_invoke = client.get("/api/v1/mcp/servers/nat")
    assert after_invoke.status_code == 200
    assert after_invoke.json()["adapter_session"]["active"] is True
    assert after_invoke.json()["adapter_session"]["initialized"] is True
    assert after_invoke.json()["adapter_session"]["last_activity_at"] is not None
    assert after_invoke.json()["adapter_session"]["freshness"] == "active_recent"

    invalidated = client.post("/api/v1/mcp/servers/nat/adapter/invalidate")
    assert invalidated.status_code == 200
    assert invalidated.json()["initialized"] is False
    assert invalidated.json()["adapter_session"]["active"] is False
    assert invalidated.json()["adapter_session"]["initialized"] is False
    assert invalidated.json()["adapter_session"]["freshness"] == "unknown"

    refreshed = client.post("/api/v1/mcp/servers/nat/adapter/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["initialized"] is True
    assert refreshed.json()["adapter_session"]["active"] is True
    assert refreshed.json()["adapter_session"]["initialized"] is True
    assert refreshed.json()["adapter_session"]["freshness"] == "active_recent"

    invoke_after_refresh = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["nat"],
        },
    )
    assert invoke_after_refresh.status_code == 200
    session_id_after_refresh = invoke_after_refresh.json()["result"]["structuredContent"][
        "session_id"
    ]
    assert session_id_after_refresh != session_id_before_refresh

    assert factory.created >= 2
    assert factory.closed >= 1


def test_mcp_adapter_session_lifecycle_conflict_without_nat_controls() -> None:
    manager = MCPClientManager(transport_adapter=FallbackTransport())
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "nat", "url": "http://nat.local"},
    )

    listing = client.get("/api/v1/mcp/servers")
    assert listing.status_code == 200
    assert listing.json()["adapter_controls_available"] is False
    assert listing.json()["items"][0]["adapter_controls_available"] is False

    invalidate = client.post("/api/v1/mcp/servers/nat/adapter/invalidate")
    assert invalidate.status_code == 409
    assert "not available" in invalidate.json()["detail"]

    refresh = client.post("/api/v1/mcp/servers/nat/adapter/refresh")
    assert refresh.status_code == 409
    assert "not available" in refresh.json()["detail"]


def test_mcp_adapter_sessions_endpoint_aggregates_status() -> None:
    factory = APIFakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "a", "url": "http://a.local"})
    client.post("/api/v1/mcp/servers", json={"name": "b", "url": "http://b.local"})

    before = client.get("/api/v1/mcp/adapter-sessions")
    assert before.status_code == 200
    assert before.json()["adapter_controls_available"] is True
    assert [item["server"] for item in before.json()["items"]] == ["a", "b"]
    assert all(item["active"] is False for item in before.json()["items"])
    assert all(item["freshness"] == "unknown" for item in before.json()["items"])

    invoke = client.post(
        "/api/v1/mcp/invoke/tool",
        json={"tool_name": "att.project.list", "arguments": {}, "preferred_servers": ["a"]},
    )
    assert invoke.status_code == 200

    after = client.get("/api/v1/mcp/adapter-sessions")
    assert after.status_code == 200
    by_name = {item["server"]: item for item in after.json()["items"]}
    assert by_name["a"]["active"] is True
    assert by_name["a"]["initialized"] is True
    assert by_name["a"]["last_activity_at"] is not None
    assert by_name["a"]["freshness"] == "active_recent"
    assert by_name["b"]["active"] is False
    assert by_name["b"]["freshness"] == "unknown"

    active_only = client.get("/api/v1/mcp/adapter-sessions", params={"active_only": True})
    assert active_only.status_code == 200
    assert [item["server"] for item in active_only.json()["items"]] == ["a"]

    server_b = client.get("/api/v1/mcp/adapter-sessions", params={"server": "b"})
    assert server_b.status_code == 200
    assert [item["server"] for item in server_b.json()["items"]] == ["b"]
    assert server_b.json()["items"][0]["active"] is False
    assert server_b.json()["items"][0]["freshness"] == "unknown"

    limited = client.get("/api/v1/mcp/adapter-sessions", params={"limit": 1})
    assert limited.status_code == 200
    assert [item["server"] for item in limited.json()["items"]] == ["b"]


def test_mcp_adapter_sessions_endpoint_without_nat_controls() -> None:
    manager = MCPClientManager(transport_adapter=FallbackTransport())
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "a", "url": "http://a.local"})
    response = client.get("/api/v1/mcp/adapter-sessions")
    assert response.status_code == 200
    assert response.json()["adapter_controls_available"] is False
    assert response.json()["items"] == []


def test_mcp_adapter_session_freshness_reports_stale_state() -> None:
    factory = APIFakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        adapter_session_stale_after_seconds=60,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "a", "url": "http://a.local"})
    invoked = client.post(
        "/api/v1/mcp/invoke/tool",
        json={"tool_name": "att.project.list", "arguments": {}, "preferred_servers": ["a"]},
    )
    assert invoked.status_code == 200

    adapter = manager._adapter_with_session_controls()
    assert adapter is not None
    adapter._sessions["a"].last_activity_at = datetime.now(UTC) - timedelta(seconds=61)

    listing = client.get("/api/v1/mcp/adapter-sessions", params={"server": "a"})
    assert listing.status_code == 200
    assert listing.json()["items"][0]["freshness"] == "stale"

    server = client.get("/api/v1/mcp/servers/a")
    assert server.status_code == 200
    assert server.json()["adapter_session"]["freshness"] == "stale"


def test_mcp_adapter_sessions_endpoint_supports_freshness_filter() -> None:
    factory = APIFakeNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        adapter_session_stale_after_seconds=60,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "a", "url": "http://a.local"})
    client.post("/api/v1/mcp/servers", json={"name": "b", "url": "http://b.local"})

    invoked = client.post(
        "/api/v1/mcp/invoke/tool",
        json={"tool_name": "att.project.list", "arguments": {}, "preferred_servers": ["a"]},
    )
    assert invoked.status_code == 200

    adapter = manager._adapter_with_session_controls()
    assert adapter is not None
    adapter._sessions["a"].last_activity_at = datetime.now(UTC) - timedelta(seconds=61)

    stale = client.get("/api/v1/mcp/adapter-sessions", params={"freshness": "stale"})
    assert stale.status_code == 200
    assert [item["server"] for item in stale.json()["items"]] == ["a"]
    assert stale.json()["items"][0]["freshness"] == "stale"

    unknown = client.get("/api/v1/mcp/adapter-sessions", params={"freshness": "unknown"})
    assert unknown.status_code == 200
    assert [item["server"] for item in unknown.json()["items"]] == ["b"]
    assert unknown.json()["items"][0]["freshness"] == "unknown"

    recent = client.get(
        "/api/v1/mcp/adapter-sessions",
        params={"freshness": "active_recent"},
    )
    assert recent.status_code == 200
    assert recent.json()["items"] == []

    server_listing = client.get("/api/v1/mcp/servers")
    assert server_listing.status_code == 200
    by_name = {item["name"]: item for item in server_listing.json()["items"]}
    assert by_name["a"]["adapter_session"]["freshness"] == "stale"
    assert by_name["b"]["adapter_session"]["freshness"] == "unknown"


def test_mcp_partial_cluster_refresh_failover_order_and_correlation() -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "primary", "url": "http://primary.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "backup", "url": "http://backup.local"},
    )

    first = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first.status_code == 200
    assert first.json()["server"] == "primary"

    refresh = client.post("/api/v1/mcp/servers/primary/adapter/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["initialized"] is True

    factory.fail_on_tool_calls.add("primary")
    second = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert second.status_code == 200
    assert second.json()["server"] == "backup"
    request_id = second.json()["request_id"]

    invocation_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id},
    )
    assert invocation_events.status_code == 200
    items = invocation_events.json()["items"]
    assert [item["phase"] for item in items] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_failure",
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in items] == [
        "primary",
        "primary",
        "primary",
        "primary",
        "backup",
        "backup",
        "backup",
        "backup",
    ]

    correlated_events = client.get(
        "/api/v1/mcp/events",
        params={"correlation_id": request_id},
    )
    assert correlated_events.status_code == 200
    correlated_items = correlated_events.json()["items"]
    assert len(correlated_items) == 1
    assert correlated_items[0]["server"] == "primary"
    assert correlated_items[0]["to_status"] == ServerStatus.DEGRADED.value
    assert correlated_items[0]["correlation_id"] == request_id


def test_mcp_invalidate_one_server_preserves_other_server_identity_and_capabilities() -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "primary", "url": "http://primary.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "backup", "url": "http://backup.local"},
    )

    first_backup = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert first_backup.status_code == 200
    assert first_backup.json()["server"] == "backup"
    backup_session_before = first_backup.json()["result"]["structuredContent"]["session_id"]

    backup_server_before = client.get("/api/v1/mcp/servers/backup")
    assert backup_server_before.status_code == 200
    backup_snapshot_before = backup_server_before.json()["capability_snapshot"]
    assert backup_snapshot_before is not None

    first_primary = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first_primary.status_code == 200
    assert first_primary.json()["server"] == "primary"

    invalidate_primary = client.post("/api/v1/mcp/servers/primary/adapter/invalidate")
    assert invalidate_primary.status_code == 200
    assert invalidate_primary.json()["adapter_session"]["active"] is False

    second_backup = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert second_backup.status_code == 200
    assert second_backup.json()["server"] == "backup"
    backup_session_after = second_backup.json()["result"]["structuredContent"]["session_id"]
    assert backup_session_after == backup_session_before

    backup_server_after = client.get("/api/v1/mcp/servers/backup")
    assert backup_server_after.status_code == 200
    backup_snapshot_after = backup_server_after.json()["capability_snapshot"]
    assert backup_snapshot_after == backup_snapshot_before

    adapter_sessions = client.get("/api/v1/mcp/adapter-sessions")
    assert adapter_sessions.status_code == 200
    by_name = {item["server"]: item for item in adapter_sessions.json()["items"]}
    assert by_name["backup"]["active"] is True
    assert by_name["primary"]["active"] is False


def test_mcp_mixed_state_refresh_invalidate_timeout_preserves_local_snapshots() -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post(
        "/api/v1/mcp/servers",
        json={"name": "primary", "url": "http://primary.local"},
    )
    client.post(
        "/api/v1/mcp/servers",
        json={"name": "backup", "url": "http://backup.local"},
    )

    first_primary = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first_primary.status_code == 200
    assert first_primary.json()["server"] == "primary"

    first_backup = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert first_backup.status_code == 200
    assert first_backup.json()["server"] == "backup"
    backup_session_before = first_backup.json()["result"]["structuredContent"]["session_id"]

    backup_before = client.get("/api/v1/mcp/servers/backup")
    assert backup_before.status_code == 200
    backup_snapshot_before = backup_before.json()["capability_snapshot"]
    assert backup_snapshot_before is not None

    primary_before = client.get("/api/v1/mcp/servers/primary")
    assert primary_before.status_code == 200
    primary_snapshot_before = primary_before.json()["capability_snapshot"]
    assert primary_snapshot_before is not None

    refresh_primary = client.post("/api/v1/mcp/servers/primary/adapter/refresh")
    assert refresh_primary.status_code == 200
    primary_snapshot_after_refresh = refresh_primary.json()["capability_snapshot"]
    assert primary_snapshot_after_refresh is not None
    assert primary_snapshot_after_refresh["captured_at"] != primary_snapshot_before["captured_at"]

    invalidate_backup = client.post("/api/v1/mcp/servers/backup/adapter/invalidate")
    assert invalidate_backup.status_code == 200
    assert invalidate_backup.json()["adapter_session"]["active"] is False
    assert invalidate_backup.json()["adapter_session"]["freshness"] == "unknown"

    factory.fail_on_timeout_tool_calls.add("primary")
    failover = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert failover.status_code == 200
    assert failover.json()["server"] == "backup"
    request_id = failover.json()["request_id"]
    backup_session_after = failover.json()["result"]["structuredContent"]["session_id"]
    assert backup_session_after != backup_session_before

    invocation_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id},
    )
    assert invocation_events.status_code == 200
    invocation_items = invocation_events.json()["items"]
    assert [item["phase"] for item in invocation_items] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_failure",
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in invocation_items] == [
        "primary",
        "primary",
        "primary",
        "primary",
        "backup",
        "backup",
        "backup",
        "backup",
    ]
    assert invocation_items[3]["error_category"] == "network_timeout"

    correlated = client.get("/api/v1/mcp/events", params={"correlation_id": request_id})
    assert correlated.status_code == 200
    correlated_items = correlated.json()["items"]
    assert len(correlated_items) == 1
    assert correlated_items[0]["server"] == "primary"
    assert correlated_items[0]["to_status"] == ServerStatus.DEGRADED.value

    primary_after = client.get("/api/v1/mcp/servers/primary")
    assert primary_after.status_code == 200
    primary_snapshot_after = primary_after.json()["capability_snapshot"]
    assert primary_snapshot_after == primary_snapshot_after_refresh

    backup_after = client.get("/api/v1/mcp/servers/backup")
    assert backup_after.status_code == 200
    backup_snapshot_after = backup_after.json()["capability_snapshot"]
    assert backup_snapshot_after is not None
    assert backup_snapshot_after["captured_at"] != backup_snapshot_before["captured_at"]
    assert backup_snapshot_after["server_info"]["name"] == "backup"
    assert primary_snapshot_after["server_info"]["name"] == "primary"

    adapter_sessions = client.get("/api/v1/mcp/adapter-sessions")
    assert adapter_sessions.status_code == 200
    by_name = {item["server"]: item for item in adapter_sessions.json()["items"]}
    assert by_name["primary"]["active"] is False
    assert by_name["primary"]["freshness"] == "unknown"
    assert by_name["backup"]["active"] is True
    assert by_name["backup"]["freshness"] == "active_recent"


def test_mcp_scripted_flapping_preserves_mixed_method_order_and_correlation() -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=3,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    factory.set_failure_script("primary", "tools/call", ["timeout", "ok"])
    factory.set_failure_script("backup", "resources/read", ["timeout", "ok"])

    first_tool = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first_tool.status_code == 200
    assert first_tool.json()["server"] == "backup"
    request_id_tool_1 = first_tool.json()["request_id"]

    tool_failover = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_tool_1},
    )
    assert tool_failover.status_code == 200
    tool_failover_items = tool_failover.json()["items"]
    assert [item["phase"] for item in tool_failover_items] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_failure",
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in tool_failover_items] == [
        "primary",
        "primary",
        "primary",
        "primary",
        "backup",
        "backup",
        "backup",
        "backup",
    ]
    assert tool_failover_items[3]["error_category"] == "network_timeout"
    assert_invocation_event_filters(
        client,
        request_id=request_id_tool_1,
        server="primary",
        method="tools/call",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_tool_1,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    clock.advance(seconds=1)

    first_resource = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert first_resource.status_code == 200
    assert first_resource.json()["server"] == "primary"
    request_id_resource_1 = first_resource.json()["request_id"]

    resource_failover = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_resource_1},
    )
    assert resource_failover.status_code == 200
    resource_failover_items = resource_failover.json()["items"]
    assert [item["phase"] for item in resource_failover_items] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_failure",
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in resource_failover_items] == [
        "backup",
        "backup",
        "backup",
        "backup",
        "primary",
        "primary",
        "primary",
        "primary",
    ]
    assert resource_failover_items[3]["error_category"] == "network_timeout"
    assert_invocation_event_filters(
        client,
        request_id=request_id_resource_1,
        server="backup",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_resource_1,
        server="backup",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    resource_correlation = client.get(
        "/api/v1/mcp/events",
        params={"correlation_id": request_id_resource_1},
    )
    assert resource_correlation.status_code == 200
    assert [item["server"] for item in resource_correlation.json()["items"]] == [
        "backup",
        "primary",
    ]
    assert [item["to_status"] for item in resource_correlation.json()["items"]] == [
        ServerStatus.DEGRADED.value,
        ServerStatus.HEALTHY.value,
    ]

    second_tool = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert second_tool.status_code == 200
    assert second_tool.json()["server"] == "primary"

    manager.record_check_result("primary", healthy=False, error="hold primary")
    clock.advance(seconds=1)
    second_resource = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["backup"],
        },
    )
    assert second_resource.status_code == 200
    assert second_resource.json()["server"] == "backup"
    request_id_resource_2 = second_resource.json()["request_id"]

    backup_recovery_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_resource_2},
    )
    assert backup_recovery_events.status_code == 200
    assert [item["phase"] for item in backup_recovery_events.json()["items"]] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in backup_recovery_events.json()["items"]] == [
        "backup",
        "backup",
        "backup",
        "backup",
    ]
    assert_connection_event_filters(
        client,
        request_id=request_id_resource_2,
        server="backup",
        expected_statuses=[ServerStatus.HEALTHY.value],
    )


def test_mcp_scripted_call_order_matches_invocation_phase_starts() -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
        unreachable_after=3,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    factory.set_failure_script("primary", "tools/call", ["timeout"])
    factory.set_failure_script("backup", "resources/read", ["timeout"])

    tool_response = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert tool_response.status_code == 200
    assert tool_response.json()["server"] == "backup"
    tool_request_id = tool_response.json()["request_id"]
    assert_invocation_event_filters(
        client,
        request_id=tool_request_id,
        server="primary",
        method="tools/call",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=tool_request_id,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    clock.advance(seconds=1)
    resource_response = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert resource_response.status_code == 200
    assert resource_response.json()["server"] == "primary"
    resource_request_id = resource_response.json()["request_id"]
    assert_invocation_event_filters(
        client,
        request_id=resource_request_id,
        server="backup",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=resource_request_id,
        server="backup",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    expected_call_order = _expected_call_order_for_requests(
        client=client,
        request_ids=(tool_request_id, resource_request_id),
    )

    observed_call_order = _collect_mixed_method_call_order(factory=factory)
    assert_call_order_subsequence(
        observed_call_order=observed_call_order,
        expected_call_order=expected_call_order,
    )


def test_mcp_repeated_same_server_calls_skip_transport_reinitialize() -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    request_specs = [
        (
            "/api/v1/mcp/invoke/tool",
            {
                "tool_name": "att.project.list",
                "arguments": {},
                "preferred_servers": ["primary"],
            },
            "tools/call",
        ),
        (
            "/api/v1/mcp/invoke/tool",
            {
                "tool_name": "att.project.list",
                "arguments": {},
                "preferred_servers": ["primary"],
            },
            "tools/call",
        ),
        (
            "/api/v1/mcp/invoke/resource",
            {
                "uri": "att://projects",
                "preferred_servers": ["primary"],
            },
            "resources/read",
        ),
        (
            "/api/v1/mcp/invoke/resource",
            {
                "uri": "att://projects",
                "preferred_servers": ["primary"],
            },
            "resources/read",
        ),
    ]
    request_ids: list[str] = []
    for path, payload, method in request_specs:
        response = client.post(path, json=payload)
        assert response.status_code == 200
        assert response.json()["server"] == "primary"
        request_id = response.json()["request_id"]
        request_ids.append(request_id)
        assert_invocation_event_filters(
            client,
            request_id=request_id,
            server="primary",
            method=method,
            expected_phases=[
                "initialize_start",
                "initialize_success",
                "invoke_start",
                "invoke_success",
            ],
        )
        assert_connection_event_filters(
            client,
            request_id=request_id,
            server="primary",
            expected_statuses=[],
        )

    expected_call_order = _expected_call_order_for_requests(
        client=client,
        request_ids=request_ids,
    )

    observed_call_order = _collect_mixed_method_call_order(factory=factory)
    assert observed_call_order == [
        ("primary", "initialize"),
        ("primary", "tools/call"),
        ("primary", "tools/call"),
        ("primary", "resources/read"),
        ("primary", "resources/read"),
    ]

    assert_call_order_subsequence(
        observed_call_order=observed_call_order,
        expected_call_order=expected_call_order,
    )


def test_mcp_force_reinitialize_triggers_add_initialize_to_call_order() -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    request_specs: list[tuple[str, dict[str, object], str, list[str]]] = [
        (
            "/api/v1/mcp/invoke/tool",
            {
                "tool_name": "att.project.list",
                "arguments": {},
                "preferred_servers": ["primary"],
            },
            "tools/call",
            [],
        ),
        (
            "/api/v1/mcp/invoke/tool",
            {
                "tool_name": "att.project.list",
                "arguments": {},
                "preferred_servers": ["primary"],
            },
            "tools/call",
            [],
        ),
        (
            "/api/v1/mcp/invoke/resource",
            {
                "uri": "att://projects",
                "preferred_servers": ["primary"],
            },
            "resources/read",
            [],
        ),
        (
            "/api/v1/mcp/invoke/resource",
            {
                "uri": "att://projects",
                "preferred_servers": ["primary"],
            },
            "resources/read",
            [ServerStatus.HEALTHY.value],
        ),
    ]

    request_ids: list[str] = []
    for index, (path, payload, method, expected_statuses) in enumerate(request_specs):
        if index == 1:
            primary = manager.get("primary")
            assert primary is not None
            primary.initialization_expires_at = clock.current - timedelta(seconds=1)
        if index == 3:
            primary = manager.get("primary")
            assert primary is not None
            primary.status = ServerStatus.DEGRADED
            primary.next_retry_at = None

        response = client.post(path, json=payload)
        assert response.status_code == 200
        assert response.json()["server"] == "primary"
        request_id = response.json()["request_id"]
        request_ids.append(request_id)
        assert_invocation_event_filters(
            client,
            request_id=request_id,
            server="primary",
            method=method,
            expected_phases=[
                "initialize_start",
                "initialize_success",
                "invoke_start",
                "invoke_success",
            ],
        )
        assert_connection_event_filters(
            client,
            request_id=request_id,
            server="primary",
            expected_statuses=expected_statuses,
        )

    expected_call_order = _expected_call_order_for_requests(
        client=client,
        request_ids=request_ids,
    )

    observed_call_order = _collect_mixed_method_call_order(factory=factory)
    assert observed_call_order == [
        ("primary", "initialize"),
        ("primary", "tools/call"),
        ("primary", "initialize"),
        ("primary", "tools/call"),
        ("primary", "resources/read"),
        ("primary", "initialize"),
        ("primary", "resources/read"),
    ]

    assert_call_order_subsequence(
        observed_call_order=observed_call_order,
        expected_call_order=expected_call_order,
    )


def test_mcp_retry_window_gating_call_order_skips_and_reenters_primary() -> None:
    harness = _create_retry_window_harness(unreachable_after=2)
    harness.factory.set_failure_script("primary", "tools/call", ["timeout", "ok"])
    invoke = _build_invoke_with_preferred(
        harness.client,
        invoke_path="/api/v1/mcp/invoke/tool",
        payload={"tool_name": "att.project.list", "arguments": {}},
    )

    sequence = _run_retry_window_gating_sequence(
        invoke=invoke,
        manager=harness.manager,
        clock=harness.clock,
        factory=harness.factory,
        third_preferred=["primary", "backup"],
    )

    request_ids = _retry_window_request_ids(sequence)
    _assert_primary_request_diagnostics(
        client=harness.client,
        method="tools/call",
        request_ids=request_ids,
        expected_phases=PRIMARY_RETRY_WINDOW_GATING_EXPECTED_PHASES,
        expected_statuses=PRIMARY_RETRY_WINDOW_GATING_EXPECTED_STATUSES,
    )
    observed_call_order = _assert_retry_window_gating_call_order_literals(
        factory=harness.factory,
        sequence=sequence,
        method="tools/call",
        expected_third_slice=RETRY_WINDOW_GATING_TOOL_EXPECTED_THIRD_SLICE,
        expected_observed_call_order=RETRY_WINDOW_GATING_TOOL_EXPECTED_OBSERVED_CALL_ORDER,
    )

    expected_call_order = _expected_call_order_for_requests(
        client=harness.client,
        request_ids=request_ids,
    )

    assert_call_order_subsequence(
        observed_call_order=observed_call_order,
        expected_call_order=expected_call_order,
    )


def test_mcp_tool_retry_window_unreachable_transition_reenters_primary() -> None:
    harness = _create_retry_window_harness(unreachable_after=2)
    harness.factory.set_failure_script("primary", "initialize", ["timeout", "timeout", "ok"])
    invoke = _build_invoke_with_preferred(
        harness.client,
        invoke_path="/api/v1/mcp/invoke/tool",
        payload={"tool_name": "att.project.list", "arguments": {}},
    )

    sequence = _run_unreachable_transition_sequence(
        invoke=invoke,
        client=harness.client,
        manager=harness.manager,
        clock=harness.clock,
        factory=harness.factory,
    )

    request_ids = _unreachable_transition_request_ids(sequence)
    _assert_primary_request_diagnostics(
        client=harness.client,
        method="tools/call",
        request_ids=request_ids,
        expected_phases=PRIMARY_UNREACHABLE_TRANSITION_EXPECTED_PHASES,
        expected_statuses=PRIMARY_UNREACHABLE_TRANSITION_EXPECTED_STATUSES,
    )
    observed_call_order = _assert_unreachable_transition_call_order_literals(
        factory=harness.factory,
        sequence=sequence,
        method="tools/call",
        expected_fifth_slice=UNREACHABLE_TRANSITION_TOOL_EXPECTED_FIFTH_SLICE,
        expected_observed_call_order=UNREACHABLE_TRANSITION_TOOL_EXPECTED_OBSERVED_CALL_ORDER,
    )

    expected_call_order = _expected_call_order_for_requests(
        client=harness.client,
        request_ids=request_ids,
    )

    assert_call_order_subsequence(
        observed_call_order=observed_call_order,
        expected_call_order=expected_call_order,
    )


def test_mcp_resource_retry_window_gating_call_order_skips_and_reenters_primary() -> None:
    harness = _create_retry_window_harness(unreachable_after=2)
    harness.factory.set_failure_script("primary", "resources/read", ["timeout", "ok"])
    invoke = _build_invoke_with_preferred(
        harness.client,
        invoke_path="/api/v1/mcp/invoke/resource",
        payload={"uri": "att://projects"},
    )

    sequence = _run_retry_window_gating_sequence(
        invoke=invoke,
        manager=harness.manager,
        clock=harness.clock,
        factory=harness.factory,
        third_preferred=["backup", "primary"],
    )

    request_ids = _retry_window_request_ids(sequence)
    _assert_primary_request_diagnostics(
        client=harness.client,
        method="resources/read",
        request_ids=request_ids,
        expected_phases=PRIMARY_RETRY_WINDOW_GATING_EXPECTED_PHASES,
        expected_statuses=PRIMARY_RETRY_WINDOW_GATING_EXPECTED_STATUSES,
    )
    observed_call_order = _assert_retry_window_gating_call_order_literals(
        factory=harness.factory,
        sequence=sequence,
        method="resources/read",
        expected_third_slice=RETRY_WINDOW_GATING_RESOURCE_EXPECTED_THIRD_SLICE,
        expected_observed_call_order=RETRY_WINDOW_GATING_RESOURCE_EXPECTED_OBSERVED_CALL_ORDER,
    )

    expected_call_order = _expected_call_order_for_requests(
        client=harness.client,
        request_ids=request_ids,
    )

    assert_call_order_subsequence(
        observed_call_order=observed_call_order,
        expected_call_order=expected_call_order,
    )


def test_mcp_resource_retry_window_unreachable_transition_reenters_primary() -> None:
    harness = _create_retry_window_harness(unreachable_after=2)
    harness.factory.set_failure_script("primary", "initialize", ["timeout", "timeout", "ok"])
    invoke = _build_invoke_with_preferred(
        harness.client,
        invoke_path="/api/v1/mcp/invoke/resource",
        payload={"uri": "att://projects"},
    )

    sequence = _run_unreachable_transition_sequence(
        invoke=invoke,
        client=harness.client,
        manager=harness.manager,
        clock=harness.clock,
        factory=harness.factory,
    )

    request_ids = _unreachable_transition_request_ids(sequence)
    _assert_primary_request_diagnostics(
        client=harness.client,
        method="resources/read",
        request_ids=request_ids,
        expected_phases=PRIMARY_UNREACHABLE_TRANSITION_EXPECTED_PHASES,
        expected_statuses=PRIMARY_UNREACHABLE_TRANSITION_EXPECTED_STATUSES,
    )
    observed_call_order = _assert_unreachable_transition_call_order_literals(
        factory=harness.factory,
        sequence=sequence,
        method="resources/read",
        expected_fifth_slice=UNREACHABLE_TRANSITION_RESOURCE_EXPECTED_FIFTH_SLICE,
        expected_observed_call_order=UNREACHABLE_TRANSITION_RESOURCE_EXPECTED_OBSERVED_CALL_ORDER,
    )

    expected_call_order = _expected_call_order_for_requests(
        client=harness.client,
        request_ids=request_ids,
    )

    assert_call_order_subsequence(
        observed_call_order=observed_call_order,
        expected_call_order=expected_call_order,
    )


@pytest.mark.parametrize(
    ("invoke_path", "payload", "method"),
    [
        (
            "/api/v1/mcp/invoke/tool",
            {"tool_name": "att.project.list", "arguments": {}},
            "tools/call",
        ),
        (
            "/api/v1/mcp/invoke/resource",
            {"uri": "att://projects"},
            "resources/read",
        ),
    ],
)
@pytest.mark.parametrize(
    ("preferred", "expected_first", "expected_second"),
    [
        (["primary", "backup"], "primary", "backup"),
        (["backup", "primary"], "backup", "primary"),
    ],
)
def test_mcp_simultaneous_unreachable_retry_window_reopen_prefers_ordered_candidates(
    invoke_path: str,
    payload: dict[str, object],
    method: str,
    preferred: list[str],
    expected_first: str,
    expected_second: str,
) -> None:
    harness = _create_retry_window_harness(unreachable_after=1)
    invoke_once = _build_invoke_with_preferred(
        harness.client,
        invoke_path=invoke_path,
        payload=payload,
    )
    sequence = _run_simultaneous_unreachable_reopen_sequence(
        invoke=invoke_once,
        client=harness.client,
        manager=harness.manager,
        clock=harness.clock,
        factory=harness.factory,
        preferred=preferred,
        expected_first=expected_first,
        expected_second=expected_second,
    )
    assert sequence.method == method

    assert_invocation_event_filters(
        harness.client,
        request_id=sequence.request_id,
        server=expected_first,
        method=method,
        expected_phases=[
            "initialize_start",
            "initialize_failure",
        ],
    )
    assert_connection_event_filters(
        harness.client,
        request_id=sequence.request_id,
        server=expected_first,
        expected_statuses=[],
    )
    assert_invocation_event_filters(
        harness.client,
        request_id=sequence.request_id,
        server=expected_second,
        method=method,
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )
    assert_connection_event_filters(
        harness.client,
        request_id=sequence.request_id,
        server=expected_second,
        expected_statuses=[ServerStatus.HEALTHY.value],
    )

    events = collect_invocation_events_for_requests(
        harness.client,
        request_ids=(sequence.request_id,),
    )
    initialize_starts = [
        str(item["server"]) for item in events if item["phase"] == "initialize_start"
    ]
    assert initialize_starts == [expected_first, expected_second]
    expected_call_order = expected_call_order_from_phase_starts(events)

    reopen_slice = [
        (server, call_method)
        for server, _, call_method in harness.factory.calls[sequence.calls_before_reopen :]
        if call_method in {"initialize", method}
    ]
    assert reopen_slice == [
        (expected_second, "initialize"),
        (expected_second, method),
    ]
    assert_call_order_subsequence(
        observed_call_order=reopen_slice,
        expected_call_order=expected_call_order,
    )


def test_mcp_scripted_initialize_and_invoke_method_isolation_across_servers() -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    factory.set_failure_script("primary", "initialize", ["ok"])
    factory.set_failure_script("backup", "initialize", ["ok"])
    factory.set_failure_script("primary", "tools/call", ["error"])
    factory.set_failure_script("primary", "resources/read", ["ok"])
    factory.set_failure_script("backup", "resources/read", ["timeout"])

    first_tool = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first_tool.status_code == 200
    assert first_tool.json()["server"] == "backup"
    request_id_1 = first_tool.json()["request_id"]

    assert factory.failure_scripts[("primary", "initialize")] == []
    assert factory.failure_scripts[("backup", "initialize")] == []
    assert factory.failure_scripts[("primary", "tools/call")] == []
    assert factory.failure_scripts[("primary", "resources/read")] == ["ok"]
    assert factory.failure_scripts[("backup", "resources/read")] == ["timeout"]
    assert_invocation_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        method="tools/call",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    manager.record_check_result("primary", healthy=True)

    second_resource = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert second_resource.status_code == 200
    assert second_resource.json()["server"] == "primary"
    request_id_2 = second_resource.json()["request_id"]

    assert factory.failure_scripts[("primary", "resources/read")] == []
    assert factory.failure_scripts[("backup", "resources/read")] == ["timeout"]
    assert_invocation_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        expected_statuses=[],
    )

    third_resource = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert third_resource.status_code == 200
    assert third_resource.json()["server"] == "primary"
    request_id_3 = third_resource.json()["request_id"]

    assert factory.failure_scripts[("backup", "resources/read")] == []
    assert_invocation_event_filters(
        client,
        request_id=request_id_3,
        server="backup",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_3,
        server="backup",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )


def test_mcp_init_script_exhaustion_falls_back_without_mutating_method_queue() -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    factory.fail_on_timeout_initialize.add("primary")
    factory.set_failure_script("primary", "initialize", ["ok"])
    factory.set_failure_script("primary", "tools/call", ["ok"])

    first_resource = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first_resource.status_code == 200
    assert first_resource.json()["server"] == "primary"
    request_id_1 = first_resource.json()["request_id"]
    assert factory.failure_scripts[("primary", "initialize")] == []
    assert factory.failure_scripts[("primary", "tools/call")] == ["ok"]
    assert_invocation_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        expected_statuses=[],
    )

    invalidated = client.post("/api/v1/mcp/servers/primary/adapter/invalidate")
    assert invalidated.status_code == 200
    second_resource = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert second_resource.status_code == 200
    assert second_resource.json()["server"] == "backup"
    request_id_2 = second_resource.json()["request_id"]

    assert factory.failure_scripts[("primary", "tools/call")] == ["ok"]
    assert_invocation_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_failure",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    manager.record_check_result("primary", healthy=True)
    factory.fail_on_timeout_initialize.remove("primary")
    third_tool = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert third_tool.status_code == 200
    assert third_tool.json()["server"] == "primary"
    request_id_3 = third_tool.json()["request_id"]
    assert factory.failure_scripts[("primary", "tools/call")] == []
    assert_invocation_event_filters(
        client,
        request_id=request_id_3,
        server="primary",
        method="tools/call",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_3,
        server="primary",
        expected_statuses=[],
    )

    primary = client.get("/api/v1/mcp/servers/primary")
    assert primary.status_code == 200
    assert primary.json()["status"] == ServerStatus.HEALTHY.value


def test_mcp_scripted_initialize_precedence_and_failover() -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        now_provider=clock,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    # Scripted initialize "ok" must override set-based initialize timeout toggles.
    factory.fail_on_timeout_initialize.add("primary")
    factory.set_failure_script("primary", "initialize", ["ok"])
    scripted_ok = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert scripted_ok.status_code == 200
    assert scripted_ok.json()["server"] == "primary"
    request_id_1 = scripted_ok.json()["request_id"]
    assert_invocation_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        method="tools/call",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        expected_statuses=[],
    )

    # Scripted initialize timeout should drive deterministic initialize-stage failover.
    invalidated = client.post("/api/v1/mcp/servers/primary/adapter/invalidate")
    assert invalidated.status_code == 200
    factory.set_failure_script("primary", "initialize", ["timeout"])
    scripted_timeout = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert scripted_timeout.status_code == 200
    assert scripted_timeout.json()["server"] == "backup"
    request_id_2 = scripted_timeout.json()["request_id"]

    failover_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_2},
    )
    assert failover_events.status_code == 200
    items = failover_events.json()["items"]
    assert [item["phase"] for item in items] == [
        "initialize_start",
        "initialize_failure",
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in items] == [
        "primary",
        "primary",
        "backup",
        "backup",
        "backup",
        "backup",
    ]
    assert items[1]["error_category"] == "network_timeout"
    assert_connection_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )


def test_mcp_resource_scripted_initialize_precedence_overrides_timeout_toggle() -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    factory.fail_on_timeout_initialize.add("primary")
    factory.set_failure_script("primary", "initialize", ["ok"])

    scripted_ok = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert scripted_ok.status_code == 200
    assert scripted_ok.json()["server"] == "primary"
    assert scripted_ok.json()["method"] == "resources/read"
    request_id_1 = scripted_ok.json()["request_id"]
    assert_invocation_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        expected_statuses=[],
    )

    invalidated = client.post("/api/v1/mcp/servers/primary/adapter/invalidate")
    assert invalidated.status_code == 200

    timeout_fallback = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert timeout_fallback.status_code == 200
    assert timeout_fallback.json()["server"] == "backup"
    assert timeout_fallback.json()["method"] == "resources/read"
    request_id_2 = timeout_fallback.json()["request_id"]

    assert_invocation_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_failure",
        ],
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    correlated = client.get("/api/v1/mcp/events", params={"correlation_id": request_id_1})
    assert correlated.status_code == 200
    assert correlated.json()["items"] == []

    primary = client.get("/api/v1/mcp/servers/primary")
    assert primary.status_code == 200
    assert primary.json()["status"] == ServerStatus.DEGRADED.value
    assert primary.json()["last_error_category"] == "network_timeout"


@pytest.mark.parametrize("error_stage", ["initialize", "invoke"])
def test_mcp_scripted_error_actions_preserve_transport_error_failover_and_correlation(
    error_stage: str,
) -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    if error_stage == "initialize":
        factory.set_failure_script("primary", "initialize", ["error"])
        expected_phases = [
            "initialize_start",
            "initialize_failure",
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ]
        expected_servers = [
            "primary",
            "primary",
            "backup",
            "backup",
            "backup",
            "backup",
        ]
        primary_expected_phases = ["initialize_start", "initialize_failure"]
        failure_event_index = 1
    else:
        factory.set_failure_script("primary", "tools/call", ["error"])
        expected_phases = [
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ]
        expected_servers = [
            "primary",
            "primary",
            "primary",
            "primary",
            "backup",
            "backup",
            "backup",
            "backup",
        ]
        primary_expected_phases = [
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
        ]
        failure_event_index = 3

    invoke = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert invoke.status_code == 200
    assert invoke.json()["server"] == "backup"
    request_id = invoke.json()["request_id"]

    invocation_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id},
    )
    assert invocation_events.status_code == 200
    items = invocation_events.json()["items"]
    assert [item["phase"] for item in items] == expected_phases
    assert [item["server"] for item in items] == expected_servers
    assert items[failure_event_index]["error_category"] == "transport_error"

    assert_invocation_event_filters(
        client,
        request_id=request_id,
        server="primary",
        method="tools/call",
        expected_phases=primary_expected_phases,
    )
    assert_connection_event_filters(
        client,
        request_id=request_id,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    correlated = client.get("/api/v1/mcp/events", params={"correlation_id": request_id})
    assert correlated.status_code == 200
    correlated_items = correlated.json()["items"]
    assert len(correlated_items) == 1
    assert correlated_items[0]["server"] == "primary"
    assert correlated_items[0]["to_status"] == ServerStatus.DEGRADED.value
    assert correlated_items[0]["correlation_id"] == request_id

    primary = client.get("/api/v1/mcp/servers/primary")
    assert primary.status_code == 200
    assert primary.json()["status"] == ServerStatus.DEGRADED.value
    assert primary.json()["last_error_category"] == "transport_error"
    assert primary.json()["retry_count"] == 1


@pytest.mark.parametrize("error_stage", ["initialize", "invoke"])
def test_mcp_resource_scripted_error_actions_preserve_transport_error_failover_and_correlation(
    error_stage: str,
) -> None:
    factory = ClusterNatSessionFactory()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    if error_stage == "initialize":
        factory.set_failure_script("primary", "initialize", ["error"])
        expected_phases = [
            "initialize_start",
            "initialize_failure",
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ]
        expected_servers = [
            "primary",
            "primary",
            "backup",
            "backup",
            "backup",
            "backup",
        ]
        primary_expected_phases = ["initialize_start", "initialize_failure"]
        failure_event_index = 1
    else:
        factory.set_failure_script("primary", "resources/read", ["error"])
        expected_phases = [
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ]
        expected_servers = [
            "primary",
            "primary",
            "primary",
            "primary",
            "backup",
            "backup",
            "backup",
            "backup",
        ]
        primary_expected_phases = [
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
        ]
        failure_event_index = 3

    invoke = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert invoke.status_code == 200
    assert invoke.json()["server"] == "backup"
    assert invoke.json()["method"] == "resources/read"
    request_id = invoke.json()["request_id"]

    invocation_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id},
    )
    assert invocation_events.status_code == 200
    items = invocation_events.json()["items"]
    assert [item["phase"] for item in items] == expected_phases
    assert [item["server"] for item in items] == expected_servers
    assert items[failure_event_index]["error_category"] == "transport_error"

    assert_invocation_event_filters(
        client,
        request_id=request_id,
        server="primary",
        method="resources/read",
        expected_phases=primary_expected_phases,
    )
    assert_connection_event_filters(
        client,
        request_id=request_id,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    correlated = client.get("/api/v1/mcp/events", params={"correlation_id": request_id})
    assert correlated.status_code == 200
    correlated_items = correlated.json()["items"]
    assert len(correlated_items) == 1
    assert correlated_items[0]["server"] == "primary"
    assert correlated_items[0]["to_status"] == ServerStatus.DEGRADED.value
    assert correlated_items[0]["correlation_id"] == request_id

    primary = client.get("/api/v1/mcp/servers/primary")
    assert primary.status_code == 200
    assert primary.json()["status"] == ServerStatus.DEGRADED.value
    assert primary.json()["last_error_category"] == "transport_error"
    assert primary.json()["retry_count"] == 1


@pytest.mark.parametrize("timeout_stage", ["initialize", "invoke"])
def test_mcp_retry_window_convergence_stage_specific_timeouts(
    timeout_stage: str,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        unreachable_after=2,
        now_provider=clock,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    warm_primary = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert warm_primary.status_code == 200
    assert warm_primary.json()["server"] == "primary"

    warm_backup = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert warm_backup.status_code == 200
    assert warm_backup.json()["server"] == "backup"

    primary_warm = client.get("/api/v1/mcp/servers/primary")
    assert primary_warm.status_code == 200
    primary_snapshot_initial = primary_warm.json()["capability_snapshot"]
    assert primary_snapshot_initial is not None

    backup_warm = client.get("/api/v1/mcp/servers/backup")
    assert backup_warm.status_code == 200
    backup_snapshot_initial = backup_warm.json()["capability_snapshot"]
    assert backup_snapshot_initial is not None

    if timeout_stage == "initialize":
        invalidated = client.post("/api/v1/mcp/servers/primary/adapter/invalidate")
        assert invalidated.status_code == 200
        assert invalidated.json()["initialized"] is False
        factory.fail_on_timeout_initialize.add("primary")
        failover_phases = [
            "initialize_start",
            "initialize_failure",
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ]
        failover_servers = [
            "primary",
            "primary",
            "backup",
            "backup",
            "backup",
            "backup",
        ]
        failover_error_index = 1
    else:
        factory.fail_on_timeout_tool_calls.add("primary")
        failover_phases = [
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ]
        failover_servers = [
            "primary",
            "primary",
            "primary",
            "primary",
            "backup",
            "backup",
            "backup",
            "backup",
        ]
        failover_error_index = 3

    first_failover = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first_failover.status_code == 200
    assert first_failover.json()["server"] == "backup"
    request_id_1 = first_failover.json()["request_id"]

    first_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_1},
    )
    assert first_events.status_code == 200
    first_items = first_events.json()["items"]
    assert [item["phase"] for item in first_items] == failover_phases
    assert [item["server"] for item in first_items] == failover_servers
    assert first_items[failover_error_index]["error_category"] == "network_timeout"
    assert_invocation_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        expected_phases=expected_phases_for_server(
            failover_phases,
            failover_servers,
            server="primary",
        ),
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    primary_after_first = client.get("/api/v1/mcp/servers/primary")
    assert primary_after_first.status_code == 200
    assert primary_after_first.json()["status"] == ServerStatus.DEGRADED.value
    assert primary_after_first.json()["retry_count"] == 1
    assert primary_after_first.json()["next_retry_at"] is not None
    assert (
        primary_after_first.json()["capability_snapshot"]["captured_at"]
        == primary_snapshot_initial["captured_at"]
    )

    during_window = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert during_window.status_code == 200
    assert during_window.json()["server"] == "backup"
    request_id_2 = during_window.json()["request_id"]

    second_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_2},
    )
    assert second_events.status_code == 200
    second_items = second_events.json()["items"]
    assert [item["phase"] for item in second_items] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in second_items] == [
        "backup",
        "backup",
        "backup",
        "backup",
    ]
    assert_invocation_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        expected_phases=[],
    )
    no_transition = client.get("/api/v1/mcp/events", params={"correlation_id": request_id_2})
    assert no_transition.status_code == 200
    assert no_transition.json()["items"] == []
    assert_connection_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        expected_statuses=[],
    )

    clock.advance(seconds=2)
    manager.record_check_result("backup", healthy=False, error="manual degrade")
    clock.advance(seconds=1)

    second_failover = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert second_failover.status_code == 200
    assert second_failover.json()["server"] == "backup"
    request_id_3 = second_failover.json()["request_id"]

    third_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_3},
    )
    assert third_events.status_code == 200
    third_items = third_events.json()["items"]
    assert [item["phase"] for item in third_items] == failover_phases
    assert [item["server"] for item in third_items] == failover_servers
    assert third_items[failover_error_index]["error_category"] == "network_timeout"
    assert_invocation_event_filters(
        client,
        request_id=request_id_3,
        server="primary",
        expected_phases=expected_phases_for_server(
            failover_phases,
            failover_servers,
            server="primary",
        ),
    )

    primary_after_second = client.get("/api/v1/mcp/servers/primary")
    assert primary_after_second.status_code == 200
    if timeout_stage == "initialize":
        assert primary_after_second.json()["status"] == ServerStatus.UNREACHABLE.value
        assert primary_after_second.json()["retry_count"] == 2
        assert (
            primary_after_second.json()["capability_snapshot"]["captured_at"]
            == primary_snapshot_initial["captured_at"]
        )
    else:
        assert primary_after_second.json()["status"] == ServerStatus.DEGRADED.value
        assert primary_after_second.json()["retry_count"] == 1
        assert (
            primary_after_second.json()["capability_snapshot"]["captured_at"]
            != primary_snapshot_initial["captured_at"]
        )

    backup_after_second = client.get("/api/v1/mcp/servers/backup")
    assert backup_after_second.status_code == 200
    assert (
        backup_after_second.json()["capability_snapshot"]["captured_at"]
        != backup_snapshot_initial["captured_at"]
    )

    stage_transition = client.get(
        "/api/v1/mcp/events",
        params={"correlation_id": request_id_3},
    )
    assert stage_transition.status_code == 200
    stage_items = stage_transition.json()["items"]
    if timeout_stage == "initialize":
        assert any(
            item["server"] == "primary" and item["to_status"] == ServerStatus.UNREACHABLE.value
            for item in stage_items
        )
        assert_connection_event_filters(
            client,
            request_id=request_id_3,
            server="primary",
            expected_statuses=[ServerStatus.UNREACHABLE.value],
        )
    else:
        assert any(
            item["server"] == "primary" and item["to_status"] == ServerStatus.HEALTHY.value
            for item in stage_items
        )
        assert any(
            item["server"] == "primary" and item["to_status"] == ServerStatus.DEGRADED.value
            for item in stage_items
        )
        assert_connection_event_filters(
            client,
            request_id=request_id_3,
            server="primary",
            expected_statuses=[
                ServerStatus.HEALTHY.value,
                ServerStatus.DEGRADED.value,
            ],
        )

    if timeout_stage == "initialize":
        factory.fail_on_timeout_initialize.remove("primary")
    else:
        factory.fail_on_timeout_tool_calls.remove("primary")
    clock.advance(seconds=3)
    manager.record_check_result("backup", healthy=False, error="hold backup")

    recovery = client.post(
        "/api/v1/mcp/invoke/tool",
        json={
            "tool_name": "att.project.list",
            "arguments": {},
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert recovery.status_code == 200
    assert recovery.json()["server"] == "primary"
    request_id_4 = recovery.json()["request_id"]

    recovery_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_4},
    )
    assert recovery_events.status_code == 200
    recovery_items = recovery_events.json()["items"]
    assert [item["phase"] for item in recovery_items] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in recovery_items] == [
        "primary",
        "primary",
        "primary",
        "primary",
    ]
    assert_invocation_event_filters(
        client,
        request_id=request_id_4,
        server="primary",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )

    correlation_recovery = client.get(
        "/api/v1/mcp/events",
        params={"correlation_id": request_id_4},
    )
    assert correlation_recovery.status_code == 200
    recovered_items = correlation_recovery.json()["items"]
    assert len(recovered_items) == 1
    assert recovered_items[0]["server"] == "primary"
    assert recovered_items[0]["to_status"] == ServerStatus.HEALTHY.value
    assert_connection_event_filters(
        client,
        request_id=request_id_4,
        server="primary",
        expected_statuses=[ServerStatus.HEALTHY.value],
    )

    primary_final = client.get("/api/v1/mcp/servers/primary")
    assert primary_final.status_code == 200
    assert primary_final.json()["status"] == ServerStatus.HEALTHY.value
    assert primary_final.json()["retry_count"] == 0
    assert (
        primary_final.json()["capability_snapshot"]["captured_at"]
        != primary_snapshot_initial["captured_at"]
    )

    primary_sessions = client.get(
        "/api/v1/mcp/adapter-sessions",
        params={"server": "primary", "freshness": "active_recent"},
    )
    assert primary_sessions.status_code == 200
    assert len(primary_sessions.json()["items"]) == 1
    assert primary_sessions.json()["items"][0]["server"] == "primary"


@pytest.mark.parametrize("timeout_stage", ["initialize", "invoke"])
def test_mcp_resource_retry_window_convergence_stage_specific_timeouts(
    timeout_stage: str,
) -> None:
    factory = ClusterNatSessionFactory()
    clock = MCPTestClock()
    manager = MCPClientManager(
        transport_adapter=NATMCPTransportAdapter(session_factory=factory),
        unreachable_after=2,
        now_provider=clock,
    )
    client = _client_with_manager(manager)

    client.post("/api/v1/mcp/servers", json={"name": "primary", "url": "http://primary.local"})
    client.post("/api/v1/mcp/servers", json={"name": "backup", "url": "http://backup.local"})

    warm_primary = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert warm_primary.status_code == 200
    assert warm_primary.json()["server"] == "primary"
    assert warm_primary.json()["method"] == "resources/read"

    warm_backup = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["backup", "primary"],
        },
    )
    assert warm_backup.status_code == 200
    assert warm_backup.json()["server"] == "backup"
    assert warm_backup.json()["method"] == "resources/read"

    primary_warm = client.get("/api/v1/mcp/servers/primary")
    assert primary_warm.status_code == 200
    primary_snapshot_initial = primary_warm.json()["capability_snapshot"]
    assert primary_snapshot_initial is not None

    backup_warm = client.get("/api/v1/mcp/servers/backup")
    assert backup_warm.status_code == 200
    backup_snapshot_initial = backup_warm.json()["capability_snapshot"]
    assert backup_snapshot_initial is not None

    if timeout_stage == "initialize":
        invalidated = client.post("/api/v1/mcp/servers/primary/adapter/invalidate")
        assert invalidated.status_code == 200
        assert invalidated.json()["initialized"] is False
        factory.fail_on_timeout_initialize.add("primary")
        failover_phases = [
            "initialize_start",
            "initialize_failure",
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ]
        failover_servers = [
            "primary",
            "primary",
            "backup",
            "backup",
            "backup",
            "backup",
        ]
        failover_error_index = 1
    else:
        factory.fail_on_timeout_resource_reads.add("primary")
        failover_phases = [
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_failure",
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ]
        failover_servers = [
            "primary",
            "primary",
            "primary",
            "primary",
            "backup",
            "backup",
            "backup",
            "backup",
        ]
        failover_error_index = 3

    first_failover = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert first_failover.status_code == 200
    assert first_failover.json()["server"] == "backup"
    assert first_failover.json()["method"] == "resources/read"
    request_id_1 = first_failover.json()["request_id"]

    first_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_1},
    )
    assert first_events.status_code == 200
    first_items = first_events.json()["items"]
    assert [item["phase"] for item in first_items] == failover_phases
    assert [item["server"] for item in first_items] == failover_servers
    assert first_items[failover_error_index]["error_category"] == "network_timeout"
    assert_invocation_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        method="resources/read",
        expected_phases=expected_phases_for_server(
            failover_phases,
            failover_servers,
            server="primary",
        ),
    )
    assert_connection_event_filters(
        client,
        request_id=request_id_1,
        server="primary",
        expected_statuses=[ServerStatus.DEGRADED.value],
    )

    primary_after_first = client.get("/api/v1/mcp/servers/primary")
    assert primary_after_first.status_code == 200
    assert primary_after_first.json()["status"] == ServerStatus.DEGRADED.value
    assert primary_after_first.json()["retry_count"] == 1
    assert primary_after_first.json()["next_retry_at"] is not None
    assert (
        primary_after_first.json()["capability_snapshot"]["captured_at"]
        == primary_snapshot_initial["captured_at"]
    )

    during_window = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert during_window.status_code == 200
    assert during_window.json()["server"] == "backup"
    assert during_window.json()["method"] == "resources/read"
    request_id_2 = during_window.json()["request_id"]

    second_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_2},
    )
    assert second_events.status_code == 200
    second_items = second_events.json()["items"]
    assert [item["phase"] for item in second_items] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in second_items] == [
        "backup",
        "backup",
        "backup",
        "backup",
    ]
    assert_invocation_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        method="resources/read",
        expected_phases=[],
    )
    no_transition = client.get("/api/v1/mcp/events", params={"correlation_id": request_id_2})
    assert no_transition.status_code == 200
    assert no_transition.json()["items"] == []
    assert_connection_event_filters(
        client,
        request_id=request_id_2,
        server="primary",
        expected_statuses=[],
    )

    clock.advance(seconds=2)
    manager.record_check_result("backup", healthy=False, error="manual degrade")
    clock.advance(seconds=1)

    second_failover = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert second_failover.status_code == 200
    assert second_failover.json()["server"] == "backup"
    assert second_failover.json()["method"] == "resources/read"
    request_id_3 = second_failover.json()["request_id"]

    third_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_3},
    )
    assert third_events.status_code == 200
    third_items = third_events.json()["items"]
    assert [item["phase"] for item in third_items] == failover_phases
    assert [item["server"] for item in third_items] == failover_servers
    assert third_items[failover_error_index]["error_category"] == "network_timeout"
    assert_invocation_event_filters(
        client,
        request_id=request_id_3,
        server="primary",
        method="resources/read",
        expected_phases=expected_phases_for_server(
            failover_phases,
            failover_servers,
            server="primary",
        ),
    )

    primary_after_second = client.get("/api/v1/mcp/servers/primary")
    assert primary_after_second.status_code == 200
    if timeout_stage == "initialize":
        assert primary_after_second.json()["status"] == ServerStatus.UNREACHABLE.value
        assert primary_after_second.json()["retry_count"] == 2
        assert (
            primary_after_second.json()["capability_snapshot"]["captured_at"]
            == primary_snapshot_initial["captured_at"]
        )
    else:
        assert primary_after_second.json()["status"] == ServerStatus.DEGRADED.value
        assert primary_after_second.json()["retry_count"] == 1
        assert (
            primary_after_second.json()["capability_snapshot"]["captured_at"]
            != primary_snapshot_initial["captured_at"]
        )

    backup_after_second = client.get("/api/v1/mcp/servers/backup")
    assert backup_after_second.status_code == 200
    assert (
        backup_after_second.json()["capability_snapshot"]["captured_at"]
        != backup_snapshot_initial["captured_at"]
    )

    stage_transition = client.get(
        "/api/v1/mcp/events",
        params={"correlation_id": request_id_3},
    )
    assert stage_transition.status_code == 200
    stage_items = stage_transition.json()["items"]
    if timeout_stage == "initialize":
        assert any(
            item["server"] == "primary" and item["to_status"] == ServerStatus.UNREACHABLE.value
            for item in stage_items
        )
        assert_connection_event_filters(
            client,
            request_id=request_id_3,
            server="primary",
            expected_statuses=[ServerStatus.UNREACHABLE.value],
        )
    else:
        assert any(
            item["server"] == "primary" and item["to_status"] == ServerStatus.HEALTHY.value
            for item in stage_items
        )
        assert any(
            item["server"] == "primary" and item["to_status"] == ServerStatus.DEGRADED.value
            for item in stage_items
        )
        assert_connection_event_filters(
            client,
            request_id=request_id_3,
            server="primary",
            expected_statuses=[
                ServerStatus.HEALTHY.value,
                ServerStatus.DEGRADED.value,
            ],
        )

    if timeout_stage == "initialize":
        factory.fail_on_timeout_initialize.remove("primary")
    else:
        factory.fail_on_timeout_resource_reads.remove("primary")
    clock.advance(seconds=3)
    manager.record_check_result("backup", healthy=False, error="hold backup")

    recovery = client.post(
        "/api/v1/mcp/invoke/resource",
        json={
            "uri": "att://projects",
            "preferred_servers": ["primary", "backup"],
        },
    )
    assert recovery.status_code == 200
    assert recovery.json()["server"] == "primary"
    assert recovery.json()["method"] == "resources/read"
    request_id_4 = recovery.json()["request_id"]

    recovery_events = client.get(
        "/api/v1/mcp/invocation-events",
        params={"request_id": request_id_4},
    )
    assert recovery_events.status_code == 200
    recovery_items = recovery_events.json()["items"]
    assert [item["phase"] for item in recovery_items] == [
        "initialize_start",
        "initialize_success",
        "invoke_start",
        "invoke_success",
    ]
    assert [item["server"] for item in recovery_items] == [
        "primary",
        "primary",
        "primary",
        "primary",
    ]
    assert_invocation_event_filters(
        client,
        request_id=request_id_4,
        server="primary",
        method="resources/read",
        expected_phases=[
            "initialize_start",
            "initialize_success",
            "invoke_start",
            "invoke_success",
        ],
    )

    correlation_recovery = client.get(
        "/api/v1/mcp/events",
        params={"correlation_id": request_id_4},
    )
    assert correlation_recovery.status_code == 200
    recovered_items = correlation_recovery.json()["items"]
    assert len(recovered_items) == 1
    assert recovered_items[0]["server"] == "primary"
    assert recovered_items[0]["to_status"] == ServerStatus.HEALTHY.value
    assert_connection_event_filters(
        client,
        request_id=request_id_4,
        server="primary",
        expected_statuses=[ServerStatus.HEALTHY.value],
    )

    primary_final = client.get("/api/v1/mcp/servers/primary")
    assert primary_final.status_code == 200
    assert primary_final.json()["status"] == ServerStatus.HEALTHY.value
    assert primary_final.json()["retry_count"] == 0
    assert (
        primary_final.json()["capability_snapshot"]["captured_at"]
        != primary_snapshot_initial["captured_at"]
    )

    primary_sessions = client.get(
        "/api/v1/mcp/adapter-sessions",
        params={"server": "primary", "freshness": "active_recent"},
    )
    assert primary_sessions.status_code == 200
    assert len(primary_sessions.json()["items"]) == 1
    assert primary_sessions.json()["items"][0]["server"] == "primary"
