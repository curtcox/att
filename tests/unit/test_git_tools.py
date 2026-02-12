from __future__ import annotations

import pytest

from att.mcp.tools.git_tools import parse_git_tool_call


def test_parse_git_status() -> None:
    call = parse_git_tool_call("att.git.status", {"project_id": "p1"})
    assert call is not None
    assert call.operation == "status"
    assert call.project_id == "p1"


def test_parse_git_commit_requires_message() -> None:
    with pytest.raises(ValueError, match="message is required"):
        parse_git_tool_call("att.git.commit", {"project_id": "p1"})


def test_parse_git_pr_create_defaults() -> None:
    call = parse_git_tool_call(
        "att.git.pr.create",
        {"project_id": "p1", "title": "feat: demo"},
    )
    assert call is not None
    assert call.operation == "pr_create"
    assert call.title == "feat: demo"
    assert call.body == ""
    assert call.base == "dev"


def test_parse_git_branch_checkout_flag() -> None:
    call = parse_git_tool_call(
        "att.git.branch",
        {"project_id": "p1", "name": "feature/x", "checkout": "false"},
    )
    assert call is not None
    assert call.operation == "branch"
    assert call.checkout is False


def test_parse_git_non_git_tool_returns_none() -> None:
    assert parse_git_tool_call("att.project.list", {}) is None
