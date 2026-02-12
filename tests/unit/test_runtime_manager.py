from __future__ import annotations

import io
from pathlib import Path

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
