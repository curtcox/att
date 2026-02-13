from __future__ import annotations

import io
import subprocess
from pathlib import Path
from urllib import error as urllib_error

from att.core.runtime_manager import RuntimeManager


class _FakeProcess:
    def __init__(self, output: str) -> None:
        self.pid = 1234
        self.stdout = io.StringIO(output)
        self._running = True
        self.terminated = False

    def poll(self) -> int | None:
        return None if self._running else 0

    def terminate(self) -> None:
        self.terminated = True
        self._running = False

    def kill(self) -> None:
        self._running = False

    def wait(self, timeout: int | float | None = None) -> int:
        del timeout
        self._running = False
        return 0


def test_runtime_manager_captures_logs(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeProcess("line-1\nline-2\n")

    def fake_popen(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return fake

    monkeypatch.setattr("att.core.runtime_manager.subprocess.Popen", fake_popen)

    manager = RuntimeManager()
    state = manager.start(tmp_path, tmp_path / "workflow.yaml")
    assert state.running is True
    assert state.pid == 1234

    # Joining reader is implicit when stop is called.
    stopped = manager.stop()
    assert stopped.running is False
    assert fake.terminated is True
    assert manager.logs() == ["line-1", "line-2"]


def test_runtime_manager_log_limit(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeProcess("a\nb\nc\n")

    def fake_popen(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return fake

    monkeypatch.setattr("att.core.runtime_manager.subprocess.Popen", fake_popen)

    manager = RuntimeManager(max_log_lines=2)
    manager.start(tmp_path, tmp_path / "workflow.yaml")
    manager.stop()

    assert manager.logs() == ["b", "c"]
    assert manager.logs(limit=1) == ["c"]


def test_runtime_manager_probe_reports_process_health(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeProcess("ready\n")

    def fake_popen(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return fake

    monkeypatch.setattr("att.core.runtime_manager.subprocess.Popen", fake_popen)

    manager = RuntimeManager()
    manager.start(tmp_path, tmp_path / "workflow.yaml")
    probe = manager.probe_health()

    assert probe.healthy is True
    assert probe.probe == "process"
    assert probe.reason == "process_running"
    manager.stop()


def test_runtime_manager_probe_reports_unhealthy_when_not_running() -> None:
    manager = RuntimeManager()
    probe = manager.probe_health()

    assert probe.healthy is False
    assert probe.probe == "process"
    assert probe.reason == "process_not_running"


def test_runtime_manager_probe_reports_http_failure(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeProcess("ready\n")

    def fake_popen(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return fake

    def fake_urlopen(url: str, timeout: float):  # type: ignore[no-untyped-def]
        del timeout
        raise urllib_error.HTTPError(url, 503, "unavailable", {}, None)

    monkeypatch.setattr("att.core.runtime_manager.subprocess.Popen", fake_popen)
    monkeypatch.setattr("att.core.runtime_manager.urllib_request.urlopen", fake_urlopen)

    manager = RuntimeManager(health_check_url="http://localhost:8000/health")
    manager.start(tmp_path, tmp_path / "workflow.yaml")
    probe = manager.probe_health()

    assert probe.healthy is False
    assert probe.probe == "http"
    assert probe.reason == "http_status:503"
    assert probe.http_status == 503
    manager.stop()


def test_runtime_manager_probe_command_transient_recovery(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeProcess("ready\n")
    command_returncodes = [1, 0]

    def fake_popen(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return fake

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return subprocess.CompletedProcess(args=["health-check"], returncode=command_returncodes.pop(0))

    monkeypatch.setattr("att.core.runtime_manager.subprocess.Popen", fake_popen)
    monkeypatch.setattr("att.core.runtime_manager.subprocess.run", fake_run)

    manager = RuntimeManager(health_check_command=["health-check"])
    manager.start(tmp_path, tmp_path / "workflow.yaml")

    first = manager.probe_health()
    second = manager.probe_health()

    assert first.healthy is False
    assert first.probe == "command"
    assert first.reason == "command_exit:1"
    assert second.healthy is True
    assert second.probe == "command"
    assert second.reason == "command_ok"
    manager.stop()


def test_runtime_manager_read_logs_with_cursor(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeProcess("line-1\nline-2\nline-3\n")

    def fake_popen(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return fake

    monkeypatch.setattr("att.core.runtime_manager.subprocess.Popen", fake_popen)

    manager = RuntimeManager()
    manager.start(tmp_path, tmp_path / "workflow.yaml")
    manager.stop()

    first = manager.read_logs(cursor=0, limit=2)
    assert first.logs == ["line-1", "line-2"]
    assert first.cursor == 2
    assert first.has_more is True
    assert first.truncated is False

    second = manager.read_logs(cursor=first.cursor, limit=10)
    assert second.logs == ["line-3"]
    assert second.cursor == 3
    assert second.has_more is False
    assert second.truncated is False


def test_runtime_manager_read_logs_marks_truncated_cursor(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeProcess("a\nb\nc\n")

    def fake_popen(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return fake

    monkeypatch.setattr("att.core.runtime_manager.subprocess.Popen", fake_popen)

    manager = RuntimeManager(max_log_lines=2)
    manager.start(tmp_path, tmp_path / "workflow.yaml")
    manager.stop()

    read = manager.read_logs(cursor=0, limit=10)
    assert read.logs == ["b", "c"]
    assert read.cursor == 3
    assert read.start_cursor == 1
    assert read.end_cursor == 3
    assert read.truncated is True
    assert read.has_more is False
