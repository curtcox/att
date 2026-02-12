"""Git tool adapters for MCP exposure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

type GitOperation = Literal[
    "status",
    "commit",
    "push",
    "branch",
    "pr_create",
    "pr_merge",
    "pr_review",
    "log",
    "actions",
]


@dataclass(slots=True)
class GitToolCall:
    """Canonical git tool call payload."""

    operation: GitOperation
    project_id: str
    message: str | None = None
    remote: str = "origin"
    branch: str = "HEAD"
    name: str | None = None
    checkout: bool = True
    title: str | None = None
    body: str = ""
    base: str = "dev"
    head: str | None = None
    pull_request: str | None = None
    strategy: str = "squash"
    limit: int | None = None


_GIT_TOOL_OPERATIONS: dict[str, GitOperation] = {
    "att.git.status": "status",
    "att.git.commit": "commit",
    "att.git.push": "push",
    "att.git.branch": "branch",
    "att.git.pr.create": "pr_create",
    "att.git.pr.merge": "pr_merge",
    "att.git.pr.review": "pr_review",
    "att.git.log": "log",
    "att.git.actions": "actions",
}


def parse_git_tool_call(tool_name: str, arguments: dict[str, Any]) -> GitToolCall | None:
    """Parse MCP git tool call into normalized payload.

    Returns `None` when the tool is not a git tool.
    Raises `ValueError` for malformed arguments.
    """
    operation = _GIT_TOOL_OPERATIONS.get(tool_name)
    if operation is None:
        return None

    project_id = _required_string(arguments, "project_id")

    if operation == "status":
        return GitToolCall(operation="status", project_id=project_id)
    if operation == "commit":
        return GitToolCall(
            operation="commit",
            project_id=project_id,
            message=_required_string(arguments, "message"),
        )
    if operation == "push":
        return GitToolCall(
            operation="push",
            project_id=project_id,
            remote=_optional_string(arguments, "remote") or "origin",
            branch=_optional_string(arguments, "branch") or "HEAD",
        )
    if operation == "branch":
        return GitToolCall(
            operation="branch",
            project_id=project_id,
            name=_required_string(arguments, "name"),
            checkout=_parse_bool(arguments.get("checkout"), default=True),
        )
    if operation == "pr_create":
        return GitToolCall(
            operation="pr_create",
            project_id=project_id,
            title=_required_string(arguments, "title"),
            body=_optional_string(arguments, "body") or "",
            base=_optional_string(arguments, "base") or "dev",
            head=_optional_string(arguments, "head"),
        )
    if operation == "pr_merge":
        return GitToolCall(
            operation="pr_merge",
            project_id=project_id,
            pull_request=_required_string(arguments, "pull_request"),
            strategy=_optional_string(arguments, "strategy") or "squash",
        )
    if operation == "pr_review":
        return GitToolCall(
            operation="pr_review",
            project_id=project_id,
            pull_request=_required_string(arguments, "pull_request"),
        )
    if operation == "log":
        return GitToolCall(
            operation="log",
            project_id=project_id,
            limit=_parse_int(arguments.get("limit"), default=20),
        )
    if operation == "actions":
        return GitToolCall(
            operation="actions",
            project_id=project_id,
            limit=_parse_int(arguments.get("limit"), default=10),
        )
    msg = f"Git tool operation not implemented: {operation}"
    raise ValueError(msg)


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


def _parse_int(value: Any, *, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default
