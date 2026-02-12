from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import get_project_manager
from att.core.project_manager import ProjectManager
from att.db.store import SQLiteStore


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_project_manager] = lambda: ProjectManager(
        SQLiteStore(tmp_path / "att.db")
    )
    return TestClient(app)


def test_e2e_health_and_mcp_discovery(tmp_path: Path) -> None:
    client = _client(tmp_path)

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    discovery = client.get("/api/v1/mcp/.well-known")
    assert discovery.status_code == 200
    payload = discovery.json()
    assert payload["name"] == "att-mcp"
    assert payload["transport"] == "streamable-http"
    assert payload["endpoint"] == "/mcp"


def test_e2e_mcp_transport_list_surface(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "smoke-1", "method": "tools/list", "params": {}},
    )
    assert response.status_code == 200
    result = response.json()["result"]
    names = {tool["name"] for tool in result["tools"]}
    assert "att.project.create" in names
    assert "att.test.run" in names
