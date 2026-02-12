import zipfile
from io import BytesIO
from pathlib import Path

import pytest
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


def test_project_clone_and_download(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = create_app()
    app.dependency_overrides[get_project_manager] = lambda: _manager_factory(tmp_path)
    client = TestClient(app)

    clone_path = tmp_path / "cloned"

    class _Process:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            clone_path.mkdir(parents=True, exist_ok=True)
            (clone_path / "README.md").write_text("demo\n", encoding="utf-8")
            return (b"ok", b"")

    async def fake_create_subprocess_exec(
        *command: str,
        stdout: int | None,
        stderr: int | None,
    ) -> _Process:
        assert command[:2] == ("git", "clone")
        assert stdout is not None
        assert stderr is not None
        return _Process()

    monkeypatch.setattr(
        "att.core.project_manager.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    cloned = client.post(
        "/api/v1/projects/clone",
        json={
            "name": "demo",
            "path": str(clone_path),
            "git_remote": "https://example.com/demo.git",
        },
    )
    assert cloned.status_code == 201
    project_id = cloned.json()["id"]

    download = client.get(f"/api/v1/projects/{project_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/zip")

    with zipfile.ZipFile(BytesIO(download.content), "r") as zip_file:
        assert "README.md" in zip_file.namelist()
