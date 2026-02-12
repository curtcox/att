"""Project tool adapters for MCP exposure."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

type ProjectOperation = Literal["create", "list", "status", "delete", "download"]


@dataclass(slots=True)
class ProjectToolCall:
    """Canonical project tool call payload."""

    operation: ProjectOperation
    project_id: str | None = None
    name: str | None = None
    path: Path | None = None
    git_remote: str | None = None
    nat_config_path: Path | None = None
    clone_from_remote: bool = False


_PROJECT_TOOL_OPERATIONS: dict[str, ProjectOperation] = {
    "att.project.create": "create",
    "att.project.list": "list",
    "att.project.status": "status",
    "att.project.delete": "delete",
    "att.project.download": "download",
}


def parse_project_tool_call(tool_name: str, arguments: dict[str, Any]) -> ProjectToolCall | None:
    """Parse MCP project tool call into normalized payload.

    Returns `None` when the tool is not a project tool.
    Raises `ValueError` for malformed arguments.
    """
    operation = _PROJECT_TOOL_OPERATIONS.get(tool_name)
    if operation is None:
        return None

    if operation == "list":
        return ProjectToolCall(operation="list")

    if operation in {"status", "delete", "download"}:
        project_id = _required_string(arguments, "project_id")
        return ProjectToolCall(operation=operation, project_id=project_id)

    name = _required_string(arguments, "name")
    path = Path(_required_string(arguments, "path"))
    git_remote = _optional_string(arguments, "git_remote")
    nat_config_raw = _optional_string(arguments, "nat_config_path")
    nat_config_path = Path(nat_config_raw) if nat_config_raw else None
    clone_from_remote = _parse_bool(
        arguments.get("clone_from_remote"), default=git_remote is not None
    )

    if clone_from_remote and git_remote is None:
        msg = "git_remote is required when clone_from_remote is true"
        raise ValueError(msg)

    return ProjectToolCall(
        operation="create",
        name=name,
        path=path,
        git_remote=git_remote,
        nat_config_path=nat_config_path,
        clone_from_remote=clone_from_remote,
    )


def _required_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if isinstance(value, str) and value.strip():
        return value
    msg = f"{key} is required"
    raise ValueError(msg)


def _optional_string(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    msg = f"{key} must be a string"
    raise ValueError(msg)


def _parse_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return default
