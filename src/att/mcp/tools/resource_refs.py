"""Resource URI adapters for MCP exposure."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs

type ResourceOperation = Literal["projects", "files", "config", "tests", "logs", "ci"]


@dataclass(slots=True)
class ResourceRef:
    """Canonical MCP resource reference."""

    operation: ResourceOperation
    project_id: str | None = None
    cursor: int | None = None
    limit: int | None = None


_PROJECT_FILES_URI = re.compile(r"^att://project/([^/]+)/files$")
_PROJECT_CONFIG_URI = re.compile(r"^att://project/([^/]+)/config$")
_PROJECT_TESTS_URI = re.compile(r"^att://project/([^/]+)/tests$")
_PROJECT_LOGS_URI = re.compile(r"^att://project/([^/]+)/logs$")
_PROJECT_CI_URI = re.compile(r"^att://project/([^/]+)/ci$")


def parse_resource_ref(uri: str) -> ResourceRef | None:
    """Parse MCP resource URI into canonical reference.

    Returns `None` when URI is unsupported.
    """
    base_uri, sep, query = uri.partition("?")
    if sep and not query:
        return None

    if base_uri == "att://projects":
        return ResourceRef(operation="projects")

    files_match = _PROJECT_FILES_URI.match(base_uri)
    if files_match:
        return ResourceRef(operation="files", project_id=files_match.group(1))

    config_match = _PROJECT_CONFIG_URI.match(base_uri)
    if config_match:
        return ResourceRef(operation="config", project_id=config_match.group(1))

    tests_match = _PROJECT_TESTS_URI.match(base_uri)
    if tests_match:
        return ResourceRef(operation="tests", project_id=tests_match.group(1))

    logs_match = _PROJECT_LOGS_URI.match(base_uri)
    if logs_match:
        cursor, limit = _parse_logs_query(query)
        return ResourceRef(
            operation="logs",
            project_id=logs_match.group(1),
            cursor=cursor,
            limit=limit,
        )

    ci_match = _PROJECT_CI_URI.match(base_uri)
    if ci_match:
        return ResourceRef(operation="ci", project_id=ci_match.group(1))

    return None


def _parse_logs_query(query: str) -> tuple[int | None, int | None]:
    if not query:
        return None, None
    parsed = parse_qs(query, strict_parsing=True)
    if not set(parsed).issubset({"cursor", "limit"}):
        msg = "unsupported query parameters for logs resource"
        raise ValueError(msg)
    cursor = _parse_optional_non_negative_int(parsed, "cursor")
    limit = _parse_optional_non_negative_int(parsed, "limit")
    return cursor, limit


def _parse_optional_non_negative_int(parsed: dict[str, list[str]], key: str) -> int | None:
    values = parsed.get(key)
    if values is None:
        return None
    if len(values) != 1:
        msg = f"{key} must be provided at most once"
        raise ValueError(msg)
    value = values[0]
    if not value.isdigit():
        msg = f"{key} must be a non-negative integer"
        raise ValueError(msg)
    return int(value)
