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


def test_mcp_transport_list_methods(tmp_path: Path) -> None:
    client = _client(tmp_path)

    initialize = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "0", "method": "initialize", "params": {}},
    )
    assert initialize.status_code == 200
    assert initialize.json()["result"]["protocolVersion"] == "2025-11-25"

    ping = client.post("/mcp", json={"jsonrpc": "2.0", "id": "0b", "method": "ping", "params": {}})
    assert ping.status_code == 200
    assert ping.json()["result"] == {}

    tools = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}},
    )
    assert tools.status_code == 200
    assert "tools" in tools.json()["result"]

    resources = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "2", "method": "resources/list", "params": {}},
    )
    assert resources.status_code == 200
    assert "resources" in resources.json()["result"]


def test_mcp_transport_tool_call_and_resource_read(tmp_path: Path) -> None:
    client = _client(tmp_path)

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)

    created = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "tools/call",
            "params": {
                "name": "att.project.create",
                "arguments": {"name": "demo", "path": str(project_path)},
            },
        },
    )
    assert created.status_code == 200
    project_id = created.json()["result"]["id"]

    write = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "4",
            "method": "tools/call",
            "params": {
                "name": "att.code.write",
                "arguments": {
                    "project_id": project_id,
                    "path": "app.py",
                    "content": "print('hi')\\n",
                },
            },
        },
    )
    assert write.status_code == 200

    read = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "5",
            "method": "tools/call",
            "params": {
                "name": "att.code.read",
                "arguments": {"project_id": project_id, "path": "app.py"},
            },
        },
    )
    assert read.status_code == 200
    assert read.json()["result"]["content"] == "print('hi')\\n"

    resource = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "6",
            "method": "resources/read",
            "params": {"uri": f"att://project/{project_id}/files"},
        },
    )
    assert resource.status_code == 200
    assert "app.py" in resource.json()["result"]["files"]

    listed = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "6a",
            "method": "tools/call",
            "params": {
                "name": "att.code.list",
                "arguments": {"project_id": project_id},
            },
        },
    )
    assert listed.status_code == 200
    assert "app.py" in listed.json()["result"]["files"]

    downloaded = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "6b",
            "method": "tools/call",
            "params": {
                "name": "att.project.download",
                "arguments": {"project_id": project_id},
            },
        },
    )
    assert downloaded.status_code == 200
    archive_path = Path(downloaded.json()["result"]["archive_path"])
    assert archive_path.suffix == ".zip"
    assert archive_path.exists()


def test_mcp_transport_reports_errors(tmp_path: Path) -> None:
    client = _client(tmp_path)

    unknown_method = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "7", "method": "unknown.method", "params": {}},
    )
    assert unknown_method.status_code == 200
    assert unknown_method.json()["error"]["code"] == -32601

    unknown_tool = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "8",
            "method": "tools/call",
            "params": {"name": "att.unknown", "arguments": {}},
        },
    )
    assert unknown_tool.status_code == 200
    assert unknown_tool.json()["error"]["code"] == -32601

    unknown_resource = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "9",
            "method": "resources/read",
            "params": {"uri": "att://unknown"},
        },
    )
    assert unknown_resource.status_code == 200
    assert unknown_resource.json()["error"]["code"] == -32000

    missing_required = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "10",
            "method": "tools/call",
            "params": {"name": "att.project.create", "arguments": {"name": "demo"}},
        },
    )
    assert missing_required.status_code == 200
    assert missing_required.json()["error"]["code"] == -32000

    clone_without_remote = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "11",
            "method": "tools/call",
            "params": {
                "name": "att.project.create",
                "arguments": {
                    "name": "demo",
                    "path": str(tmp_path / "clone-project"),
                    "clone_from_remote": True,
                },
            },
        },
    )
    assert clone_without_remote.status_code == 200
    assert clone_without_remote.json()["error"]["code"] == -32000

    git_commit_missing_message = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "12",
            "method": "tools/call",
            "params": {
                "name": "att.git.commit",
                "arguments": {"project_id": "p1"},
            },
        },
    )
    assert git_commit_missing_message.status_code == 200
    assert git_commit_missing_message.json()["error"]["code"] == -32000

    runtime_start_missing_config = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "13",
            "method": "tools/call",
            "params": {
                "name": "att.runtime.start",
                "arguments": {"project_id": "p1"},
            },
        },
    )
    assert runtime_start_missing_config.status_code == 200
    assert runtime_start_missing_config.json()["error"]["code"] == -32000

    test_run_missing_project = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "14",
            "method": "tools/call",
            "params": {
                "name": "att.test.run",
                "arguments": {"suite": "unit"},
            },
        },
    )
    assert test_run_missing_project.status_code == 200
    assert test_run_missing_project.json()["error"]["code"] == -32000
