from att.mcp.server import find_tool, registered_resources, registered_tools


def test_registered_tools_contains_expected_surface() -> None:
    tools = registered_tools()
    names = {tool.name for tool in tools}

    assert len(tools) == 30
    assert "att.project.create" in names
    assert "att.code.search" in names
    assert "att.git.pr.create" in names
    assert "att.runtime.status" in names
    assert "att.deploy.status" in names


def test_registered_resources_contains_expected_uris() -> None:
    resources = registered_resources()
    uris = {resource.uri for resource in resources}

    assert len(resources) == 6
    assert "att://projects" in uris
    assert "att://project/{id}/files" in uris
    assert "att://project/{id}/ci" in uris


def test_find_tool_returns_none_when_missing() -> None:
    assert find_tool("att.unknown") is None


def test_find_tool_returns_match_when_present() -> None:
    tool = find_tool("att.runtime.start")
    assert tool is not None
    assert tool.description
