"""Code tool adapters for MCP exposure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

type CodeOperation = Literal["list", "read", "write", "search", "diff"]


@dataclass(slots=True)
class CodeToolCall:
    """Canonical code tool call payload."""

    operation: CodeOperation
    project_id: str | None = None
    path: str | None = None
    content: str | None = None
    pattern: str | None = None
    original: str | None = None
    updated: str | None = None
    from_name: str = "original"
    to_name: str = "updated"


_CODE_TOOL_OPERATIONS: dict[str, CodeOperation] = {
    "att.code.list": "list",
    "att.code.read": "read",
    "att.code.write": "write",
    "att.code.search": "search",
    "att.code.diff": "diff",
}


def parse_code_tool_call(tool_name: str, arguments: dict[str, Any]) -> CodeToolCall | None:
    """Parse MCP code tool call into normalized payload.

    Returns `None` when the tool is not a code tool.
    Raises `ValueError` for malformed arguments.
    """
    operation = _CODE_TOOL_OPERATIONS.get(tool_name)
    if operation is None:
        return None

    if operation == "diff":
        return CodeToolCall(
            operation="diff",
            original=_required_string(arguments, "original"),
            updated=_required_string(arguments, "updated"),
            from_name=_optional_string(arguments, "from_name") or "original",
            to_name=_optional_string(arguments, "to_name") or "updated",
        )

    project_id = _required_string(arguments, "project_id")
    if operation == "list":
        return CodeToolCall(operation="list", project_id=project_id)
    if operation == "read":
        return CodeToolCall(
            operation="read",
            project_id=project_id,
            path=_required_string(arguments, "path"),
        )
    if operation == "write":
        return CodeToolCall(
            operation="write",
            project_id=project_id,
            path=_required_string(arguments, "path"),
            content=_required_content(arguments, "content"),
        )
    if operation == "search":
        return CodeToolCall(
            operation="search",
            project_id=project_id,
            pattern=_required_string(arguments, "pattern"),
        )
    msg = f"Code tool operation not implemented: {operation}"
    raise ValueError(msg)


def _required_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if isinstance(value, str) and value.strip():
        return value
    msg = f"{key} is required"
    raise ValueError(msg)


def _required_content(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if isinstance(value, str):
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
