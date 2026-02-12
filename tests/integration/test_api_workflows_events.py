from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import get_project_manager, get_store, get_tool_orchestrator
from att.core.code_manager import CodeManager
from att.core.git_manager import GitResult
from att.core.project_manager import ProjectManager
from att.core.test_runner import RunResult
from att.core.tool_orchestrator import ToolOrchestrator
from att.db.store import SQLiteStore


class FakeGitManager:
    def commit(self, project_path: Path, message: str) -> GitResult:
        return GitResult(command="git commit", output=f"committed:{message}")

    def status(self, project_path: Path) -> GitResult:
        return GitResult(command="git status --short", output="M app.py")


class FakeTestRunner:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode

    def run(self, project_path: Path, suite: str = "unit") -> RunResult:
        return RunResult(command=f"pytest tests/{suite}", returncode=self.returncode, output="ok")


def _setup_app(tmp_path: Path) -> tuple[TestClient, SQLiteStore]:
    app = create_app()
    store = SQLiteStore(tmp_path / "att.db")
    project_manager = ProjectManager(store)
    orchestrator = ToolOrchestrator(
        code_manager=CodeManager(),
        git_manager=FakeGitManager(),
        test_runner=FakeTestRunner(returncode=0),
        store=store,
    )

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_project_manager] = lambda: project_manager
    app.dependency_overrides[get_tool_orchestrator] = lambda: orchestrator

    return TestClient(app), store


def test_change_workflow_and_event_listing(tmp_path: Path) -> None:
    client, _store = _setup_app(tmp_path)

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "app.py").write_text("print('old')\n", encoding="utf-8")

    create = client.post(
        "/api/v1/projects",
        json={"name": "demo", "path": str(project_path)},
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    run = client.post(
        f"/api/v1/projects/{project_id}/workflows/change-test",
        json={
            "file_path": "app.py",
            "content": "print('new')\n",
            "suite": "unit",
            "commit_message": "feat: api",
        },
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["test_returncode"] == 0
    assert payload["committed"] is True
    assert len(payload["event_ids"]) == 4

    events = client.get(f"/api/v1/projects/{project_id}/events")
    assert events.status_code == 200
    assert len(events.json()["items"]) == 5  # includes project.created

    filtered = client.get(
        f"/api/v1/projects/{project_id}/events",
        params={"event_type": "test.passed"},
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["items"]) == 1


def test_events_endpoint_rejects_invalid_event_type(tmp_path: Path) -> None:
    client, _store = _setup_app(tmp_path)

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)

    create = client.post(
        "/api/v1/projects",
        json={"name": "demo", "path": str(project_path)},
    )
    project_id = create.json()["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/events",
        params={"event_type": "unknown.event"},
    )
    assert response.status_code == 400
