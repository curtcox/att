from __future__ import annotations

import pytest

from att.mcp.tools.debug_tools import parse_debug_tool_call


def test_parse_debug_errors() -> None:
    call = parse_debug_tool_call("att.debug.errors", {"project_id": "p1"})
    assert call is not None
    assert call.operation == "errors"
    assert call.project_id == "p1"


def test_parse_debug_logs_with_query() -> None:
    call = parse_debug_tool_call(
        "att.debug.logs",
        {"project_id": "p1", "query": "traceback"},
    )
    assert call is not None
    assert call.operation == "logs"
    assert call.project_id == "p1"
    assert call.query == "traceback"


def test_parse_debug_requires_project_id() -> None:
    with pytest.raises(ValueError, match="project_id is required"):
        parse_debug_tool_call("att.debug.errors", {})


def test_parse_debug_non_debug_tool_returns_none() -> None:
    assert parse_debug_tool_call("att.code.read", {}) is None
