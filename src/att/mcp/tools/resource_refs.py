"""Resource URI adapters for MCP exposure."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

type ResourceOperation = Literal["projects", "files", "config", "tests", "logs", "ci"]


@dataclass(slots=True)
class ResourceRef:
    """Canonical MCP resource reference."""

    operation: ResourceOperation
    project_id: str | None = None


_PROJECT_FILES_URI = re.compile(r"^att://project/([^/]+)/files$")
_PROJECT_CONFIG_URI = re.compile(r"^att://project/([^/]+)/config$")
_PROJECT_TESTS_URI = re.compile(r"^att://project/([^/]+)/tests$")
_PROJECT_LOGS_URI = re.compile(r"^att://project/([^/]+)/logs$")
_PROJECT_CI_URI = re.compile(r"^att://project/([^/]+)/ci$")


def parse_resource_ref(uri: str) -> ResourceRef | None:
    """Parse MCP resource URI into canonical reference.

    Returns `None` when URI is unsupported.
    """
    if uri == "att://projects":
        return ResourceRef(operation="projects")

    files_match = _PROJECT_FILES_URI.match(uri)
    if files_match:
        return ResourceRef(operation="files", project_id=files_match.group(1))

    config_match = _PROJECT_CONFIG_URI.match(uri)
    if config_match:
        return ResourceRef(operation="config", project_id=config_match.group(1))

    tests_match = _PROJECT_TESTS_URI.match(uri)
    if tests_match:
        return ResourceRef(operation="tests", project_id=tests_match.group(1))

    logs_match = _PROJECT_LOGS_URI.match(uri)
    if logs_match:
        return ResourceRef(operation="logs", project_id=logs_match.group(1))

    ci_match = _PROJECT_CI_URI.match(uri)
    if ci_match:
        return ResourceRef(operation="ci", project_id=ci_match.group(1))

    return None
