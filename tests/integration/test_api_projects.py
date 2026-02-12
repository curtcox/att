from pathlib import Path

from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import get_project_manager
from att.core.project_manager import ProjectManager
from att.db.store import SQLiteStore


def _manager_factory(tmp_path: Path) -> ProjectManager:
    return ProjectManager(SQLiteStore(tmp_path / "att.db"))


def test_project_crud(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_project_manager] = lambda: _manager_factory(tmp_path)

    client = TestClient(app)

    create = client.post(
        "/api/v1/projects",
        json={"name": "demo", "path": str(tmp_path / "project")},
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    listing = client.get("/api/v1/projects")
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1

    fetched = client.get(f"/api/v1/projects/{project_id}")
    assert fetched.status_code == 200

    deleted = client.delete(f"/api/v1/projects/{project_id}")
    assert deleted.status_code == 204
