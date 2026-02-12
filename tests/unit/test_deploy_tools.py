from __future__ import annotations

from pathlib import Path

import pytest

from att.mcp.tools.deploy_tools import parse_deploy_tool_call


def test_parse_deploy_build() -> None:
    call = parse_deploy_tool_call("att.deploy.build", {"project_id": "p1"})
    assert call is not None
    assert call.operation == "build"
    assert call.project_id == "p1"


def test_parse_deploy_run_with_config_path() -> None:
    call = parse_deploy_tool_call(
        "att.deploy.run",
        {"project_id": "p1", "config_path": "configs/app.yaml"},
    )
    assert call is not None
    assert call.operation == "run"
    assert call.config_path == Path("configs/app.yaml")


def test_parse_deploy_run_requires_config_path() -> None:
    with pytest.raises(ValueError, match="config_path is required"):
        parse_deploy_tool_call("att.deploy.run", {"project_id": "p1"})


def test_parse_deploy_non_deploy_tool_returns_none() -> None:
    assert parse_deploy_tool_call("att.runtime.start", {}) is None
