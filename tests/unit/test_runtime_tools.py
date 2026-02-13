from __future__ import annotations

from pathlib import Path

import pytest

from att.mcp.tools.runtime_tools import parse_runtime_tool_call


def test_parse_runtime_start() -> None:
    call = parse_runtime_tool_call(
        "att.runtime.start",
        {"project_id": "p1", "config_path": "configs/app.yaml"},
    )
    assert call is not None
    assert call.operation == "start"
    assert call.project_id == "p1"
    assert call.config_path == Path("configs/app.yaml")


def test_parse_runtime_start_requires_config_path() -> None:
    with pytest.raises(ValueError, match="config_path is required"):
        parse_runtime_tool_call("att.runtime.start", {"project_id": "p1"})


def test_parse_runtime_non_runtime_tool_returns_none() -> None:
    assert parse_runtime_tool_call("att.project.list", {}) is None


def test_parse_runtime_logs_with_cursor_and_limit() -> None:
    call = parse_runtime_tool_call(
        "att.runtime.logs",
        {"project_id": "p1", "cursor": 3, "limit": 5},
    )
    assert call is not None
    assert call.operation == "logs"
    assert call.project_id == "p1"
    assert call.cursor == 3
    assert call.limit == 5


def test_parse_runtime_logs_rejects_negative_cursor() -> None:
    with pytest.raises(ValueError, match="cursor must be a non-negative integer"):
        parse_runtime_tool_call(
            "att.runtime.logs",
            {"project_id": "p1", "cursor": -1},
        )
