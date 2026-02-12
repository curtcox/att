from __future__ import annotations

import pytest

from att.mcp.tools.code_tools import parse_code_tool_call


def test_parse_code_list_tool() -> None:
    call = parse_code_tool_call("att.code.list", {"project_id": "p1"})
    assert call is not None
    assert call.operation == "list"
    assert call.project_id == "p1"


def test_parse_code_write_requires_content() -> None:
    with pytest.raises(ValueError, match="content is required"):
        parse_code_tool_call(
            "att.code.write",
            {"project_id": "p1", "path": "app.py"},
        )


def test_parse_code_diff_payload() -> None:
    call = parse_code_tool_call(
        "att.code.diff",
        {
            "original": "a\n",
            "updated": "b\n",
            "from_name": "a/file.txt",
            "to_name": "b/file.txt",
        },
    )
    assert call is not None
    assert call.operation == "diff"
    assert call.original == "a\n"
    assert call.updated == "b\n"
    assert call.from_name == "a/file.txt"
    assert call.to_name == "b/file.txt"


def test_parse_code_non_code_tool_returns_none() -> None:
    assert parse_code_tool_call("att.project.list", {}) is None
