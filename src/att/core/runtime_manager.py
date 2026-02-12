"""Runtime process manager for nat serve."""

from __future__ import annotations

import subprocess
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RuntimeState:
    """Current runtime status."""

    running: bool
    pid: int | None = None


class RuntimeManager:
    """Manage one nat process at a time."""

    def __init__(self, *, max_log_lines: int = 1000) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._max_log_lines = max_log_lines
        self._logs: deque[str] = deque(maxlen=max_log_lines)
        self._logs_lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None

    def start(self, project_path: Path, config_path: Path) -> RuntimeState:
        if self._process and self._process.poll() is None:
            return RuntimeState(running=True, pid=self._process.pid)

        with self._logs_lock:
            self._logs.clear()

        self._process = subprocess.Popen(
            ["nat", "serve", "--config", str(config_path)],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._start_reader(self._process)
        return RuntimeState(running=True, pid=self._process.pid)

    def stop(self) -> RuntimeState:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
        self._process = None
        self._join_reader()
        return RuntimeState(running=False, pid=None)

    def status(self) -> RuntimeState:
        if self._process and self._process.poll() is None:
            return RuntimeState(running=True, pid=self._process.pid)
        self._process = None
        return RuntimeState(running=False, pid=None)

    def logs(self, *, limit: int | None = None) -> list[str]:
        with self._logs_lock:
            entries = list(self._logs)
        if limit is None or limit <= 0:
            return entries
        return entries[-limit:]

    def _start_reader(self, process: subprocess.Popen[str]) -> None:
        reader = threading.Thread(
            target=self._drain_output,
            args=(process,),
            daemon=True,
        )
        self._reader_thread = reader
        reader.start()

    def _join_reader(self) -> None:
        if self._reader_thread is not None and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        self._reader_thread = None

    def _drain_output(self, process: subprocess.Popen[str]) -> None:
        stream = process.stdout
        if stream is None:
            return
        try:
            for line in stream:
                with self._logs_lock:
                    self._logs.append(line.rstrip("\n"))
        finally:
            stream.close()
