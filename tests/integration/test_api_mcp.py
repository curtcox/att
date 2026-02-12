from __future__ import annotations

from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import get_mcp_client_manager
from att.mcp.client import ExternalServer, MCPClientManager, ServerStatus


class StaticProbe:
    def __init__(self, healthy: bool, error: str | None = None) -> None:
        self._healthy = healthy
        self._error = error

    async def __call__(self, _: ExternalServer) -> tuple[bool, str | None]:
        return self._healthy, self._error


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

    listing = client.get("/api/v1/mcp/servers")
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1

    checked = client.post("/api/v1/mcp/servers/codex/health-check")
    assert checked.status_code == 200
    assert checked.json()["status"] == ServerStatus.HEALTHY.value


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

    missing = client.post("/api/v1/mcp/servers/missing/health-check")
    assert missing.status_code == 404


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
