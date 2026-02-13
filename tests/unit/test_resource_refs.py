from __future__ import annotations

import pytest

from att.mcp.tools.resource_refs import parse_resource_ref


def test_parse_projects_resource() -> None:
    ref = parse_resource_ref("att://projects")
    assert ref is not None
    assert ref.operation == "projects"
    assert ref.project_id is None


def test_parse_project_files_resource() -> None:
    ref = parse_resource_ref("att://project/p1/files")
    assert ref is not None
    assert ref.operation == "files"
    assert ref.project_id == "p1"


def test_parse_project_ci_resource() -> None:
    ref = parse_resource_ref("att://project/p1/ci")
    assert ref is not None
    assert ref.operation == "ci"
    assert ref.project_id == "p1"


def test_parse_unknown_resource_returns_none() -> None:
    assert parse_resource_ref("att://unknown") is None


def test_parse_project_logs_resource_with_query() -> None:
    ref = parse_resource_ref("att://project/p1/logs?cursor=10&limit=25")
    assert ref is not None
    assert ref.operation == "logs"
    assert ref.project_id == "p1"
    assert ref.cursor == 10
    assert ref.limit == 25


def test_parse_project_logs_resource_rejects_invalid_query() -> None:
    with pytest.raises(ValueError, match="unsupported query parameters for logs resource"):
        parse_resource_ref("att://project/p1/logs?foo=bar")
