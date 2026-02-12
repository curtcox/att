"""Deploy tool adapters for MCP exposure."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

type DeployOperation = Literal["build", "run", "status"]


@dataclass(slots=True)
class DeployToolCall:
    """Canonical deploy tool call payload."""

    operation: DeployOperation
    project_id: str
    config_path: Path | None = None


_DEPLOY_TOOL_OPERATIONS: dict[str, DeployOperation] = {
    "att.deploy.build": "build",
    "att.deploy.run": "run",
    "att.deploy.status": "status",
}


def parse_deploy_tool_call(tool_name: str, arguments: dict[str, Any]) -> DeployToolCall | None:
    """Parse MCP deploy tool call into normalized payload.

    Returns `None` when the tool is not a deploy tool.
    Raises `ValueError` for malformed arguments.
    """
    operation = _DEPLOY_TOOL_OPERATIONS.get(tool_name)
    if operation is None:
        return None

    project_id = _required_string(arguments, "project_id")
    if operation == "run":
        return DeployToolCall(
            operation="run",
            project_id=project_id,
            config_path=Path(_required_string(arguments, "config_path")),
        )
    return DeployToolCall(operation=operation, project_id=project_id)


def _required_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if isinstance(value, str) and value.strip():
        return value
    msg = f"{key} is required"
    raise ValueError(msg)
