"""Self-bootstrap API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SelfBootstrapRequestModel(BaseModel):
    """Run request for self-bootstrap cycle."""

    file_path: str
    content: str
    commit_message: str
    suite: str = "unit"
    branch_name: str | None = None
    ci_timeout_seconds: int = 600
    ci_initial_poll_seconds: int = 10
    ci_max_poll_seconds: int = 60
    create_pr: bool = True
    auto_merge_on_ci_success: bool = True
    deploy_target: str | None = None
    requested_release_id: str | None = None
    previous_release_id: str | None = None
    rollback_release_id: str | None = None
    health_check_target: str | None = None
    health_check_retries: int = 1
    health_check_interval_seconds: int = 5
    restart_watchdog_retries: int = 3
    restart_watchdog_interval_seconds: int = 5


class SelfBootstrapResponseModel(BaseModel):
    """Self-bootstrap cycle execution result."""

    branch_name: str
    committed: bool
    pushed: bool
    ci_status: str
    pr_url: str | None
    merged: bool
    restart_watchdog_status: str
    restart_watchdog_reason: str | None = None
    health_status: str
    rollback_performed: bool
    rollback_succeeded: bool | None
    deployed_release_id: str | None = None
    rollback_target_release_id: str | None = None
    release_metadata_source: str | None = None
    success: bool
    test_returncode: int
    event_ids: list[str] = Field(default_factory=list)
