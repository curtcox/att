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
