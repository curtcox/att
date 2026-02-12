"""Test tool adapters for MCP exposure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

type TestOperation = Literal["run", "results"]


@dataclass(slots=True)
class MCPTestToolCall:
    """Canonical test tool call payload."""

    operation: TestOperation
    project_id: str
    suite: str = "unit"


_TEST_TOOL_OPERATIONS: dict[str, TestOperation] = {
    "att.test.run": "run",
    "att.test.results": "results",
}


def parse_test_tool_call(tool_name: str, arguments: dict[str, Any]) -> MCPTestToolCall | None:
    """Parse MCP test tool call into normalized payload.

    Returns `None` when the tool is not a test tool.
    Raises `ValueError` for malformed arguments.
    """
    operation = _TEST_TOOL_OPERATIONS.get(tool_name)
    if operation is None:
        return None
    project_id = _required_string(arguments, "project_id")
    suite = _optional_string(arguments, "suite") or "unit"
    return MCPTestToolCall(operation=operation, project_id=project_id, suite=suite)


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
