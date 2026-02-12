"""Project tool adapters for MCP exposure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProjectToolCall:
    """Canonical project tool call payload."""

    operation: str
    payload: dict[str, str]
