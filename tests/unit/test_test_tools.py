from __future__ import annotations

import pytest

from att.mcp.tools.test_tools import parse_test_tool_call


def test_parse_test_run_defaults_suite() -> None:
    call = parse_test_tool_call("att.test.run", {"project_id": "p1"})
    assert call is not None
    assert call.operation == "run"
    assert call.project_id == "p1"
    assert call.suite == "unit"


def test_parse_test_results() -> None:
    call = parse_test_tool_call("att.test.results", {"project_id": "p1"})
    assert call is not None
    assert call.operation == "results"
    assert call.project_id == "p1"


def test_parse_test_requires_project_id() -> None:
    with pytest.raises(ValueError, match="project_id is required"):
        parse_test_tool_call("att.test.run", {})


def test_parse_test_non_test_tool_returns_none() -> None:
    assert parse_test_tool_call("att.code.read", {}) is None


def test_parse_test_run_with_markers_and_timeout() -> None:
    call = parse_test_tool_call(
        "att.test.run",
        {"project_id": "p1", "suite": "integration", "markers": "slow", "timeout_seconds": 30},
    )
    assert call is not None
    assert call.operation == "run"
    assert call.markers == "slow"
    assert call.timeout_seconds == 30


def test_parse_test_timeout_must_be_positive_int() -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be a positive integer"):
        parse_test_tool_call("att.test.run", {"project_id": "p1", "timeout_seconds": 0})
