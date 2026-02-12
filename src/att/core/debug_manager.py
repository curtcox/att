"""Debugging helpers for runtime logs and errors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DebugSnapshot:
    """Captured debug information."""

    errors: list[str]
    logs: list[str]


class DebugManager:
    """Extract errors and filter logs."""

    def errors(self, logs: list[str]) -> list[str]:
        tokens = ("error", "exception", "traceback")
        return [line for line in logs if any(token in line.lower() for token in tokens)]

    def filter_logs(self, logs: list[str], query: str) -> list[str]:
        q = query.lower()
        return [line for line in logs if q in line.lower()]

    def snapshot(self, logs: list[str], query: str = "") -> DebugSnapshot:
        filtered = self.filter_logs(logs, query) if query else logs
        return DebugSnapshot(errors=self.errors(filtered), logs=filtered)
