"""Integration helpers for self-bootstrap provider hooks."""

from __future__ import annotations

import json
from typing import Any, Literal

type CIStatus = Literal["pending", "success", "failure"]


def parse_gh_actions_status(raw_output: str, branch_name: str) -> CIStatus:
    """Parse `gh run list --json ...` output into normalized CI status."""
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError:
        return "pending"

    if not isinstance(payload, list):
        return "pending"

    matching_runs: list[dict[str, Any]] = [
        item for item in payload if isinstance(item, dict) and item.get("headBranch") == branch_name
    ]
    if not matching_runs:
        return "pending"

    latest = matching_runs[0]
    status = str(latest.get("status", "")).lower()
    conclusion = str(latest.get("conclusion", "")).lower()

    if status in {"queued", "in_progress", "waiting", "pending", "requested"}:
        return "pending"
    if status == "completed":
        if conclusion in {"success", "neutral", "skipped"}:
            return "success"
        return "failure"

    return "pending"
