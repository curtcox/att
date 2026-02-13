"""Runtime process manager for nat serve."""

from __future__ import annotations

import subprocess
import threading
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request


@dataclass(slots=True)
class RuntimeState:
    """Current runtime status."""

    running: bool
    pid: int | None = None
    returncode: int | None = None


@dataclass(slots=True)
class RuntimeHealthProbe:
    """Health probe result for the managed runtime."""

    healthy: bool
    running: bool
    pid: int | None
    probe: str
    reason: str
    checked_at: datetime
    returncode: int | None = None
    http_status: int | None = None
    command: str | None = None


@dataclass(slots=True)
class RuntimeLogRead:
    """Runtime log read payload with cursor metadata."""

    logs: list[str]
    cursor: int
    start_cursor: int
    end_cursor: int
    truncated: bool
    has_more: bool


class RuntimeManager:
    """Manage one nat process at a time."""

    def __init__(
        self,
        *,
        max_log_lines: int = 1000,
        health_check_url: str | None = None,
        health_check_command: Sequence[str] | None = None,
        health_timeout_seconds: float = 2.0,
    ) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._max_log_lines = max_log_lines
        self._logs: deque[str] = deque(maxlen=max_log_lines)
        self._logs_lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._next_log_cursor = 0
        self._project_path: Path | None = None
        self._health_check_url = health_check_url
        self._health_check_command = tuple(health_check_command) if health_check_command else None
        self._health_timeout_seconds = health_timeout_seconds

    def start(self, project_path: Path, config_path: Path) -> RuntimeState:
        if self._process and self._process.poll() is None:
            return RuntimeState(running=True, pid=self._process.pid, returncode=None)

        with self._logs_lock:
            self._logs.clear()
            self._next_log_cursor = 0

        self._project_path = project_path
        self._process = subprocess.Popen(
            ["nat", "serve", "--config", str(config_path)],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._start_reader(self._process)
        return RuntimeState(running=True, pid=self._process.pid, returncode=None)

    def stop(self) -> RuntimeState:
        returncode: int | None = None
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                returncode = self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                returncode = self._process.wait(timeout=5)
        elif self._process is not None:
            returncode = self._process.poll()
        self._process = None
        self._join_reader()
        return RuntimeState(running=False, pid=None, returncode=returncode)

    def status(self) -> RuntimeState:
        if self._process and self._process.poll() is None:
            return RuntimeState(running=True, pid=self._process.pid, returncode=None)
        returncode = self._process.poll() if self._process is not None else None
        self._process = None
        self._join_reader()
        return RuntimeState(running=False, pid=None, returncode=returncode)

    def probe_health(
        self,
        *,
        url: str | None = None,
        command: Sequence[str] | None = None,
        timeout_seconds: float | None = None,
    ) -> RuntimeHealthProbe:
        state = self.status()
        checked_at = datetime.now(UTC)
        if not state.running:
            reason = (
                f"process_exited:{state.returncode}"
                if state.returncode is not None
                else "process_not_running"
            )
            return RuntimeHealthProbe(
                healthy=False,
                running=False,
                pid=None,
                probe="process",
                reason=reason,
                checked_at=checked_at,
                returncode=state.returncode,
            )

        probe_timeout = (
            timeout_seconds if timeout_seconds is not None else self._health_timeout_seconds
        )
        probe_command = tuple(command) if command else self._health_check_command
        if probe_command is not None:
            return self._run_command_probe(
                state=state,
                checked_at=checked_at,
                command=probe_command,
                timeout_seconds=probe_timeout,
            )

        probe_url = url or self._health_check_url
        if probe_url is not None:
            return self._run_http_probe(
                state=state,
                checked_at=checked_at,
                url=probe_url,
                timeout_seconds=probe_timeout,
            )

        return RuntimeHealthProbe(
            healthy=True,
            running=True,
            pid=state.pid,
            probe="process",
            reason="process_running",
            checked_at=checked_at,
        )

    def logs(self, *, limit: int | None = None) -> list[str]:
        return self.read_logs(limit=limit).logs

    def read_logs(self, *, cursor: int | None = None, limit: int | None = None) -> RuntimeLogRead:
        with self._logs_lock:
            entries = list(self._logs)
            end_cursor = self._next_log_cursor

        first_cursor = end_cursor - len(entries)

        if cursor is None:
            if limit is None or limit <= 0:
                logs = entries
                start_cursor = first_cursor
            else:
                logs = entries[-limit:]
                start_cursor = end_cursor - len(logs)
            return RuntimeLogRead(
                logs=logs,
                cursor=end_cursor,
                start_cursor=start_cursor,
                end_cursor=end_cursor,
                truncated=False,
                has_more=False,
            )

        requested_cursor = max(0, cursor)
        truncated = requested_cursor < first_cursor
        effective_cursor = min(max(requested_cursor, first_cursor), end_cursor)
        start_index = effective_cursor - first_cursor
        logs = entries[start_index:]
        if limit is not None and limit > 0:
            logs = logs[:limit]
        next_cursor = effective_cursor + len(logs)

        return RuntimeLogRead(
            logs=logs,
            cursor=next_cursor,
            start_cursor=effective_cursor,
            end_cursor=end_cursor,
            truncated=truncated,
            has_more=next_cursor < end_cursor,
        )

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
                    self._next_log_cursor += 1
        finally:
            stream.close()

    def _run_command_probe(
        self,
        *,
        state: RuntimeState,
        checked_at: datetime,
        command: tuple[str, ...],
        timeout_seconds: float,
    ) -> RuntimeHealthProbe:
        try:
            completed = subprocess.run(
                list(command),
                cwd=self._project_path,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return RuntimeHealthProbe(
                healthy=False,
                running=True,
                pid=state.pid,
                probe="command",
                reason="command_timeout",
                checked_at=checked_at,
                command=" ".join(command),
            )
        except OSError as exc:
            return RuntimeHealthProbe(
                healthy=False,
                running=True,
                pid=state.pid,
                probe="command",
                reason=f"command_error:{exc.__class__.__name__}",
                checked_at=checked_at,
                command=" ".join(command),
            )

        healthy = completed.returncode == 0
        reason = "command_ok" if healthy else f"command_exit:{completed.returncode}"
        return RuntimeHealthProbe(
            healthy=healthy,
            running=True,
            pid=state.pid,
            probe="command",
            reason=reason,
            checked_at=checked_at,
            returncode=completed.returncode,
            command=" ".join(command),
        )

    def _run_http_probe(
        self,
        *,
        state: RuntimeState,
        checked_at: datetime,
        url: str,
        timeout_seconds: float,
    ) -> RuntimeHealthProbe:
        try:
            with urllib_request.urlopen(url, timeout=timeout_seconds) as response:
                status_code = response.getcode()
        except urllib_error.HTTPError as exc:
            return RuntimeHealthProbe(
                healthy=False,
                running=True,
                pid=state.pid,
                probe="http",
                reason=f"http_status:{exc.code}",
                checked_at=checked_at,
                http_status=exc.code,
            )
        except urllib_error.URLError:
            return RuntimeHealthProbe(
                healthy=False,
                running=True,
                pid=state.pid,
                probe="http",
                reason="http_error",
                checked_at=checked_at,
            )

        if status_code is None:
            return RuntimeHealthProbe(
                healthy=False,
                running=True,
                pid=state.pid,
                probe="http",
                reason="http_status:unknown",
                checked_at=checked_at,
            )

        healthy = 200 <= status_code < 400
        reason = "http_ok" if healthy else f"http_status:{status_code}"
        return RuntimeHealthProbe(
            healthy=healthy,
            running=True,
            pid=state.pid,
            probe="http",
            reason=reason,
            checked_at=checked_at,
            http_status=status_code,
        )
