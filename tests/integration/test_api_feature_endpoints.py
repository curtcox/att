from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from att.api.app import create_app
from att.api.deps import (
    get_code_manager,
    get_debug_log_store,
    get_debug_manager,
    get_deploy_manager,
    get_git_manager,
    get_project_manager,
    get_runtime_manager,
    get_test_result_store,
    get_test_runner,
)
from att.core.code_manager import CodeManager
from att.core.debug_manager import DebugManager
from att.core.deploy_manager import DeployStatus
from att.core.git_manager import GitResult
from att.core.project_manager import ProjectManager
from att.core.runtime_manager import RuntimeState
from att.core.test_runner import RunResult
from att.db.store import SQLiteStore


class FakeGitManager:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def status(self, project_path: Path) -> GitResult:
        self.calls.append(f"status:{project_path}")
        return GitResult(command="git status --short", output="M README.md")

    def commit(self, project_path: Path, message: str) -> GitResult:
        self.calls.append(f"commit:{message}")
        return GitResult(command="git commit", output=f"committed:{message}")

    def push(self, project_path: Path, remote: str = "origin", branch: str = "HEAD") -> GitResult:
        self.calls.append(f"push:{remote}:{branch}")
        return GitResult(command="git push", output=f"pushed:{remote}/{branch}")

    def branch(self, project_path: Path, name: str, *, checkout: bool = True) -> GitResult:
        self.calls.append(f"branch:{name}:{checkout}")
        return GitResult(command="git branch", output=f"branch:{name}")

    def log(self, project_path: Path, limit: int = 20) -> GitResult:
        self.calls.append(f"log:{limit}")
        return GitResult(command="git log", output="abc123 init")

    def actions(self, project_path: Path, limit: int = 10) -> GitResult:
        self.calls.append(f"actions:{limit}")
        return GitResult(command="gh run list", output='[{"status":"completed"}]')

    def pr_create(
        self,
        project_path: Path,
        *,
        title: str,
        body: str,
        base: str = "dev",
        head: str | None = None,
    ) -> GitResult:
        self.calls.append(f"pr_create:{title}:{base}:{head}")
        return GitResult(command="gh pr create", output="https://example.com/pr/1")

    def pr_merge(
        self,
        project_path: Path,
        *,
        pull_request: str,
        strategy: str = "squash",
    ) -> GitResult:
        self.calls.append(f"pr_merge:{pull_request}:{strategy}")
        return GitResult(command="gh pr merge", output="merged")

    def pr_reviews(self, project_path: Path, *, pull_request: str) -> GitResult:
        self.calls.append(f"pr_reviews:{pull_request}")
        return GitResult(command="gh pr view", output='{"reviews":[]}')


class FakeRuntimeManager:
    def __init__(self) -> None:
        self.running = False
        self.pid: int | None = None

    def start(self, project_path: Path, config_path: Path) -> RuntimeState:
        self.running = True
        self.pid = 4242
        return RuntimeState(running=True, pid=self.pid)

    def stop(self) -> RuntimeState:
        self.running = False
        self.pid = None
        return RuntimeState(running=False, pid=None)

    def status(self) -> RuntimeState:
        return RuntimeState(running=self.running, pid=self.pid)


class FakeTestRunner:
    def run(self, project_path: Path, suite: str = "unit") -> RunResult:
        return RunResult(
            command=f"pytest tests/{suite}",
            returncode=0,
            output=f"{suite}:ok",
        )


class FakeDeployManager:
    def __init__(self) -> None:
        self.running = False

    def build(self, project_path: Path) -> DeployStatus:
        return DeployStatus(built=True, running=self.running, message="build ok")

    def run(self, project_path: Path, config_path: Path) -> DeployStatus:
        self.running = True
        return DeployStatus(built=True, running=True, message=f"run:{config_path.name}")

    def status(self) -> DeployStatus:
        return DeployStatus(built=True, running=self.running, message="status ok")


def _client_with_project(
    tmp_path: Path,
) -> tuple[TestClient, str, dict[str, list[str]], dict[str, dict[str, str | int]], FakeGitManager]:
    app = create_app()

    project_manager = ProjectManager(SQLiteStore(tmp_path / "att.db"))
    code_manager = CodeManager()
    debug_manager = DebugManager()
    git_manager = FakeGitManager()
    runtime_manager = FakeRuntimeManager()
    test_runner = FakeTestRunner()
    deploy_manager = FakeDeployManager()
    debug_logs: dict[str, list[str]] = {}
    test_results: dict[str, dict[str, str | int]] = {}

    app.dependency_overrides[get_project_manager] = lambda: project_manager
    app.dependency_overrides[get_code_manager] = lambda: code_manager
    app.dependency_overrides[get_debug_manager] = lambda: debug_manager
    app.dependency_overrides[get_git_manager] = lambda: git_manager
    app.dependency_overrides[get_runtime_manager] = lambda: runtime_manager
    app.dependency_overrides[get_test_runner] = lambda: test_runner
    app.dependency_overrides[get_deploy_manager] = lambda: deploy_manager
    app.dependency_overrides[get_debug_log_store] = lambda: debug_logs
    app.dependency_overrides[get_test_result_store] = lambda: test_results

    client = TestClient(app)

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)

    create = client.post(
        "/api/v1/projects",
        json={"name": "demo", "path": str(project_path)},
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    return client, project_id, debug_logs, test_results, git_manager


def test_code_endpoints_round_trip(tmp_path: Path) -> None:
    client, project_id, _, _, _ = _client_with_project(tmp_path)

    write = client.put(
        f"/api/v1/projects/{project_id}/files/src/app.py",
        json={"content": "print('hello')\n"},
    )
    assert write.status_code == 200

    read = client.get(f"/api/v1/projects/{project_id}/files/src/app.py")
    assert read.status_code == 200
    assert read.json()["content"] == "print('hello')\n"

    listing = client.get(f"/api/v1/projects/{project_id}/files")
    assert listing.status_code == 200
    assert "src/app.py" in listing.json()["files"]

    search = client.post(
        f"/api/v1/projects/{project_id}/files/search",
        json={"pattern": "hello"},
    )
    assert search.status_code == 200
    assert search.json()["matches"] == ["src/app.py"]

    diff = client.get(
        f"/api/v1/projects/{project_id}/files/diff",
        params={
            "original": "old line",
            "updated": "new line",
            "from_name": "a/file.txt",
            "to_name": "b/file.txt",
        },
    )
    assert diff.status_code == 200
    assert "new line" in diff.json()["diff"]


def test_git_endpoints(tmp_path: Path) -> None:
    client, project_id, _, _, git_manager = _client_with_project(tmp_path)

    assert client.get(f"/api/v1/projects/{project_id}/git/status").status_code == 200
    assert (
        client.post(
            f"/api/v1/projects/{project_id}/git/commit",
            json={"message": "feat: test"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/projects/{project_id}/git/push",
            json={"remote": "origin", "branch": "main"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/projects/{project_id}/git/branch",
            json={"name": "feature/test", "checkout": True},
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/projects/{project_id}/git/log").status_code == 200

    actions = client.get(f"/api/v1/projects/{project_id}/git/actions")
    assert actions.status_code == 200
    assert "actions" in actions.json()

    assert (
        client.post(
            f"/api/v1/projects/{project_id}/git/pr",
            json={"title": "feat: demo", "body": "desc", "base": "dev", "head": "feature/demo"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/projects/{project_id}/git/pr/merge",
            json={"pull_request": "123", "strategy": "squash"},
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/projects/{project_id}/git/pr/reviews",
            params={"pull_request": "123"},
        ).status_code
        == 200
    )

    assert any(call.startswith("status:") for call in git_manager.calls)
    assert "commit:feat: test" in git_manager.calls
    assert "actions:10" in git_manager.calls
    assert "pr_merge:123:squash" in git_manager.calls


def test_runtime_and_deploy_endpoints(tmp_path: Path) -> None:
    client, project_id, _, _, _ = _client_with_project(tmp_path)

    config_path = tmp_path / "project" / "nat.yaml"
    config_path.write_text("name: demo\n", encoding="utf-8")

    start = client.post(
        f"/api/v1/projects/{project_id}/runtime/start",
        json={"config_path": str(config_path)},
    )
    assert start.status_code == 200
    assert start.json()["running"] is True
    assert start.json()["pid"] == 4242

    status = client.get(f"/api/v1/projects/{project_id}/runtime/status")
    assert status.status_code == 200
    assert status.json()["running"] is True

    logs = client.get(f"/api/v1/projects/{project_id}/runtime/logs")
    assert logs.status_code == 200
    assert logs.json()["logs"] == []

    stop = client.post(f"/api/v1/projects/{project_id}/runtime/stop")
    assert stop.status_code == 200
    assert stop.json()["running"] is False

    build = client.post(f"/api/v1/projects/{project_id}/deploy/build")
    assert build.status_code == 200
    assert build.json()["built"] is True

    run = client.post(
        f"/api/v1/projects/{project_id}/deploy/run",
        json={"config_path": str(config_path)},
    )
    assert run.status_code == 200
    assert run.json()["running"] is True

    deploy_status = client.get(f"/api/v1/projects/{project_id}/deploy/status")
    assert deploy_status.status_code == 200
    assert deploy_status.json()["running"] is True


def test_test_and_debug_endpoints(tmp_path: Path) -> None:
    client, project_id, debug_logs, _, _ = _client_with_project(tmp_path)

    debug_logs[project_id] = [
        "INFO boot",
        "ERROR exploded",
        "Traceback: sample",
    ]

    run = client.post(f"/api/v1/projects/{project_id}/test/run", json={"suite": "unit"})
    assert run.status_code == 200
    assert run.json()["returncode"] == 0

    results = client.get(f"/api/v1/projects/{project_id}/test/results")
    assert results.status_code == 200
    assert results.json()["output"] == "unit:ok"

    errors = client.get(f"/api/v1/projects/{project_id}/debug/errors")
    assert errors.status_code == 200
    assert len(errors.json()["errors"]) == 2

    filtered = client.get(f"/api/v1/projects/{project_id}/debug/logs", params={"query": "exploded"})
    assert filtered.status_code == 200
    assert filtered.json()["logs"] == ["ERROR exploded"]


def test_feature_endpoints_validate_project_exists(tmp_path: Path) -> None:
    client, _, _, _, _ = _client_with_project(tmp_path)
    missing = "does-not-exist"
    diff_params = {
        "original": "a",
        "updated": "b",
        "from_name": "a/file.txt",
        "to_name": "b/file.txt",
    }

    assert client.get(f"/api/v1/projects/{missing}/files").status_code == 404
    assert (
        client.get(f"/api/v1/projects/{missing}/files/diff", params=diff_params).status_code == 404
    )
    assert client.get(f"/api/v1/projects/{missing}/git/status").status_code == 404
    assert client.get(f"/api/v1/projects/{missing}/git/actions").status_code == 404
    assert client.get(f"/api/v1/projects/{missing}/runtime/status").status_code == 404
    assert client.get(f"/api/v1/projects/{missing}/runtime/logs").status_code == 404
    assert client.get(f"/api/v1/projects/{missing}/test/results").status_code == 404
    assert client.get(f"/api/v1/projects/{missing}/debug/logs").status_code == 404
    assert client.get(f"/api/v1/projects/{missing}/deploy/status").status_code == 404
