"""ATT MCP server tool/resource catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(slots=True)
class MCPTool:
    """MCP tool descriptor exposed by ATT."""

    name: str
    description: str


@dataclass(slots=True)
class MCPResource:
    """MCP resource descriptor exposed by ATT."""

    uri: str
    description: str


_REGISTERED_TOOLS: Final[list[MCPTool]] = [
    MCPTool(
        name="att.project.create",
        description="Create a new NAT project from template or clone URL",
    ),
    MCPTool(name="att.project.download", description="Download a pre-built project artifact"),
    MCPTool(name="att.project.list", description="List all projects"),
    MCPTool(name="att.project.status", description="Get project status"),
    MCPTool(name="att.project.delete", description="Delete a project"),
    MCPTool(name="att.code.list", description="List file tree for project"),
    MCPTool(name="att.code.read", description="Read file contents"),
    MCPTool(name="att.code.write", description="Write or update file contents"),
    MCPTool(name="att.code.search", description="Search across project files"),
    MCPTool(name="att.code.diff", description="Show diff of pending changes"),
    MCPTool(name="att.git.status", description="Get git status for project"),
    MCPTool(name="att.git.commit", description="Stage and commit project changes"),
    MCPTool(name="att.git.push", description="Push commits to remote"),
    MCPTool(name="att.git.branch", description="Create or switch branches"),
    MCPTool(name="att.git.pr.create", description="Create pull request"),
    MCPTool(name="att.git.pr.merge", description="Merge pull request"),
    MCPTool(name="att.git.pr.review", description="Retrieve PR review comments"),
    MCPTool(name="att.git.log", description="Get git log"),
    MCPTool(name="att.git.actions", description="Get GitHub Actions status and logs"),
    MCPTool(name="att.runtime.start", description="Start NAT workflow server"),
    MCPTool(name="att.runtime.stop", description="Stop NAT workflow server"),
    MCPTool(name="att.runtime.logs", description="Get runtime logs"),
    MCPTool(name="att.runtime.status", description="Get runtime status"),
    MCPTool(name="att.test.run", description="Run test suite"),
    MCPTool(name="att.test.results", description="Get latest test results"),
    MCPTool(name="att.debug.errors", description="Get current error snapshots"),
    MCPTool(name="att.debug.logs", description="Get filtered debug logs"),
    MCPTool(name="att.deploy.build", description="Build deployable artifact"),
    MCPTool(name="att.deploy.run", description="Deploy to runtime target"),
    MCPTool(name="att.deploy.status", description="Get current deploy status"),
]

_REGISTERED_RESOURCES: Final[list[MCPResource]] = [
    MCPResource(uri="att://projects", description="List of all projects"),
    MCPResource(uri="att://project/{id}/files", description="Project file tree"),
    MCPResource(uri="att://project/{id}/config", description="NAT config for project"),
    MCPResource(uri="att://project/{id}/tests", description="Latest test results"),
    MCPResource(uri="att://project/{id}/logs", description="Runtime logs"),
    MCPResource(uri="att://project/{id}/ci", description="CI pipeline status"),
]


def registered_tools() -> list[MCPTool]:
    """Return all ATT MCP tools."""
    return list(_REGISTERED_TOOLS)


def registered_resources() -> list[MCPResource]:
    """Return all ATT MCP resources."""
    return list(_REGISTERED_RESOURCES)


def find_tool(name: str) -> MCPTool | None:
    """Look up one MCP tool by name."""
    for tool in _REGISTERED_TOOLS:
        if tool.name == name:
            return tool
    return None
