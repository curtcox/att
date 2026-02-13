from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import get_project_manager, get_self_bootstrap_manager
from att.core.project_manager import ProjectManager
from att.core.self_bootstrap_manager import SelfBootstrapRequest, SelfBootstrapResult
from att.core.test_runner import RunResult
from att.core.tool_orchestrator import WorkflowRunResult
from att.db.store import SQLiteStore
from att.models.events import ATTEvent, EventType


class FakeSelfBootstrapManager:
    async def execute(self, request: SelfBootstrapRequest) -> SelfBootstrapResult:
        return SelfBootstrapResult(
            branch_name=request.branch_name or "codex/fake-branch",
            committed=True,
            pushed=True,
            ci_status="success",
            pr_url="https://example.com/pr/1",
            merged=True,
            restart_watchdog_status="stable",
            restart_watchdog_reason="runtime_healthy",
            health_status="healthy",
            rollback_performed=False,
            rollback_succeeded=None,
            deployed_release_id="release-2",
            rollback_target_release_id="release-1",
            release_metadata_source="git",
            success=True,
            workflow_result=WorkflowRunResult(
                diff="diff",
                test_result=RunResult(command="pytest", returncode=0, output="ok"),
                committed=True,
                commit_output="done",
                events=[
                    ATTEvent(
                        project_id=request.project_id, event_type=EventType.CODE_CHANGED, payload={}
                    ),
                    ATTEvent(
                        project_id=request.project_id, event_type=EventType.TEST_RUN, payload={}
                    ),
                ],
            ),
        )


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    store = SQLiteStore(tmp_path / "att.db")
    manager = ProjectManager(store)

    app.dependency_overrides[get_project_manager] = lambda: manager
    app.dependency_overrides[get_self_bootstrap_manager] = lambda: FakeSelfBootstrapManager()

    return TestClient(app)


def test_self_bootstrap_run_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)

    created = client.post(
        "/api/v1/projects",
        json={"name": "demo", "path": str(project_path)},
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/self-bootstrap/run",
        json={
            "file_path": "app.py",
            "content": "print('x')\n",
            "commit_message": "feat: x",
            "branch_name": "codex/self-bootstrap-demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["committed"] is True
    assert payload["branch_name"] == "codex/self-bootstrap-demo"
    assert payload["pr_url"] == "https://example.com/pr/1"
    assert payload["merged"] is True
    assert payload["restart_watchdog_status"] == "stable"
    assert payload["restart_watchdog_reason"] == "runtime_healthy"
    assert payload["deployed_release_id"] == "release-2"
    assert payload["rollback_target_release_id"] == "release-1"
    assert payload["release_metadata_source"] == "git"
    assert payload["test_returncode"] == 0
    assert len(payload["event_ids"]) == 2


def test_self_bootstrap_run_requires_project(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/api/v1/projects/missing/self-bootstrap/run",
        json={
            "file_path": "app.py",
            "content": "print('x')\n",
            "commit_message": "feat: x",
        },
    )

    assert response.status_code == 404
