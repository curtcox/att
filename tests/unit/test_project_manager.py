import zipfile
from pathlib import Path

import pytest

from att.core.project_manager import CreateProjectInput, ProjectManager
from att.db.store import SQLiteStore
from att.models.project import ProjectStatus


@pytest.mark.asyncio
async def test_project_manager_create_and_list(tmp_path: Path) -> None:
    manager = ProjectManager(SQLiteStore(tmp_path / "att.db"))
    created = await manager.create(CreateProjectInput(name="demo", path=tmp_path / "demo"))

    projects = await manager.list()
    assert len(projects) == 1
    assert projects[0].id == created.id


@pytest.mark.asyncio
async def test_project_manager_clone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = ProjectManager(SQLiteStore(tmp_path / "att.db"))
    destination = tmp_path / "cloned"

    class _Process:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "README.md").write_text("demo\n", encoding="utf-8")
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

    project = await manager.clone(
        CreateProjectInput(
            name="demo",
            path=destination,
            git_remote="https://example.com/demo.git",
        )
    )

    assert project.path == destination
    assert project.status == ProjectStatus.CLONED
    assert (destination / "README.md").exists()


@pytest.mark.asyncio
async def test_project_manager_download_archive(tmp_path: Path) -> None:
    manager = ProjectManager(SQLiteStore(tmp_path / "att.db"))
    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "README.md").write_text("hello\n", encoding="utf-8")
    created = await manager.create(CreateProjectInput(name="demo", path=project_path))

    archive = await manager.download(created.id)

    assert archive.exists()
    assert archive.suffix == ".zip"
    with zipfile.ZipFile(archive, "r") as zip_file:
        assert "README.md" in zip_file.namelist()
