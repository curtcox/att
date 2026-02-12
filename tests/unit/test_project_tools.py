from __future__ import annotations

from pathlib import Path

import pytest

from att.mcp.tools.project_tools import parse_project_tool_call


def test_parse_project_list_tool() -> None:
    call = parse_project_tool_call("att.project.list", {})
    assert call is not None
    assert call.operation == "list"


def test_parse_project_status_requires_project_id() -> None:
    with pytest.raises(ValueError, match="project_id is required"):
        parse_project_tool_call("att.project.status", {})


def test_parse_project_create_payload() -> None:
    call = parse_project_tool_call(
        "att.project.create",
        {
            "name": "demo",
            "path": "/tmp/demo",
            "nat_config_path": "configs/app.yaml",
        },
    )
    assert call is not None
    assert call.operation == "create"
    assert call.name == "demo"
    assert call.path == Path("/tmp/demo")
    assert call.nat_config_path == Path("configs/app.yaml")
    assert call.clone_from_remote is False


def test_parse_project_create_clone_requires_git_remote() -> None:
    with pytest.raises(ValueError, match="git_remote is required when clone_from_remote is true"):
        parse_project_tool_call(
            "att.project.create",
            {
                "name": "demo",
                "path": "/tmp/demo",
                "clone_from_remote": True,
            },
        )


def test_parse_project_create_infers_clone_when_git_remote_present() -> None:
    call = parse_project_tool_call(
        "att.project.create",
        {
            "name": "demo",
            "path": "/tmp/demo",
            "git_remote": "https://example.com/demo.git",
        },
    )
    assert call is not None
    assert call.operation == "create"
    assert call.clone_from_remote is True
    assert call.git_remote == "https://example.com/demo.git"


def test_parse_project_non_project_tool_returns_none() -> None:
    assert parse_project_tool_call("att.code.read", {"project_id": "p1"}) is None
