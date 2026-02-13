from __future__ import annotations

from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import get_mcp_client_manager
from att.mcp.client import (
    ExternalServer,
    JSONObject,
    MCPClientManager,
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
