"""Runtime tool adapters for MCP exposure."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

type RuntimeOperation = Literal["start", "stop", "status", "logs"]


@dataclass(slots=True)
class RuntimeToolCall:
    """Canonical runtime tool call payload."""

    operation: RuntimeOperation
    project_id: str
    config_path: Path | None = None
    cursor: int | None = None
    limit: int | None = None


_RUNTIME_TOOL_OPERATIONS: dict[str, RuntimeOperation] = {
    "att.runtime.start": "start",
    "att.runtime.stop": "stop",
    "att.runtime.status": "status",
    "att.runtime.logs": "logs",
}


def parse_runtime_tool_call(tool_name: str, arguments: dict[str, Any]) -> RuntimeToolCall | None:
    """Parse MCP runtime tool call into normalized payload.

    Returns `None` when the tool is not a runtime tool.
    Raises `ValueError` for malformed arguments.
    """
    operation = _RUNTIME_TOOL_OPERATIONS.get(tool_name)
    if operation is None:
        return None

    project_id = _required_string(arguments, "project_id")
    if operation == "start":
        return RuntimeToolCall(
            operation="start",
            project_id=project_id,
            config_path=Path(_required_string(arguments, "config_path")),
        )
    if operation == "logs":
        return RuntimeToolCall(
            operation="logs",
            project_id=project_id,
            cursor=_optional_non_negative_int(arguments, "cursor"),
            limit=_optional_non_negative_int(arguments, "limit"),
        )
    return RuntimeToolCall(operation=operation, project_id=project_id)


def _required_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if isinstance(value, str) and value.strip():
        return value
    msg = f"{key} is required"
    raise ValueError(msg)


def _optional_non_negative_int(arguments: dict[str, Any], key: str) -> int | None:
    value = arguments.get(key)
    if value is None:
        return None
    if isinstance(value, int) and value >= 0:
        return value
    msg = f"{key} must be a non-negative integer"
    raise ValueError(msg)
