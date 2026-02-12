"""Debug tool adapters for MCP exposure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

type DebugOperation = Literal["errors", "logs"]


@dataclass(slots=True)
class DebugToolCall:
    """Canonical debug tool call payload."""

    operation: DebugOperation
    project_id: str
    query: str = ""


_DEBUG_TOOL_OPERATIONS: dict[str, DebugOperation] = {
    "att.debug.errors": "errors",
    "att.debug.logs": "logs",
}


def parse_debug_tool_call(tool_name: str, arguments: dict[str, Any]) -> DebugToolCall | None:
    """Parse MCP debug tool call into normalized payload.

    Returns `None` when the tool is not a debug tool.
    Raises `ValueError` for malformed arguments.
    """
    operation = _DEBUG_TOOL_OPERATIONS.get(tool_name)
    if operation is None:
        return None

    project_id = _required_string(arguments, "project_id")
    if operation == "errors":
        return DebugToolCall(operation="errors", project_id=project_id)
    return DebugToolCall(
        operation="logs",
        project_id=project_id,
        query=_optional_string(arguments, "query") or "",
    )


def _required_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if isinstance(value, str) and value.strip():
        return value
    msg = f"{key} is required"
    raise ValueError(msg)


def _optional_string(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    msg = f"{key} must be a string"
    raise ValueError(msg)
