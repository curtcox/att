from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import get_mcp_client_manager
from att.mcp.client import (
    ExternalServer,
    JSONObject,
    MCPClientManager,
    MCPTransportError,
    ServerStatus,
)


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
    manager = MCPClientManager(probe=StaticProbe(healthy=True), transport=transport)
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
    primary.last_initialized_at = datetime.now(UTC)
    primary.initialization_expires_at = datetime.now(UTC) + timedelta(seconds=120)

    recovered = manager.get("recovered")
    assert recovered is not None
    recovered.status = ServerStatus.HEALTHY
    recovered.initialized = False

    manager.record_check_result("degraded", healthy=False, error="down")
    degraded = manager.get("degraded")
    assert degraded is not None
    degraded.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)

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

    invocation_filtered = client.get(
        "/api/v1/mcp/invocation-events",
        params={"server": "codex", "method": "tools/call", "request_id": request_id},
    )
    assert invocation_filtered.status_code == 200
    filtered_items = invocation_filtered.json()["items"]
    assert [item["phase"] for item in filtered_items] == [
        "initialize_start",
        "initialize_failure",
    ]
    assert all(item["request_id"] == request_id for item in filtered_items)

    invocation_limited = client.get("/api/v1/mcp/invocation-events", params={"limit": 2})
    assert invocation_limited.status_code == 200
    limited_invocation_items = invocation_limited.json()["items"]
    assert [item["phase"] for item in limited_invocation_items] == [
        "invoke_start",
        "invoke_success",
    ]

    correlated_connection = client.get("/api/v1/mcp/events", params={"correlation_id": request_id})
    assert correlated_connection.status_code == 200
    correlated_items = correlated_connection.json()["items"]
    assert len(correlated_items) == 1
    assert correlated_items[0]["server"] == "codex"
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
