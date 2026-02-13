# P16 - self_bootstrap

## Status
in_progress

## Phase
1.5

## Dependencies
P04-P13

## Scope
- Define concrete implementation tasks.
- Define required tests and acceptance criteria.
- Track delivery notes and unresolved risks.

## Acceptance Criteria
- The implementation is merged with passing CI checks.
- Tests for this plan item exist and cover baseline behavior.
- `todo/master_plan.md` is updated with completion status.

## Notes
- Implemented baseline `SelfBootstrapManager` in `src/att/core/self_bootstrap_manager.py`.
- Manager now coordinates: branch creation, change workflow execution, push, optional CI polling with exponential backoff, and optional health-check gating.
- Manager now also supports PR lifecycle hooks (create PR and optional auto-merge on green CI) and rollback execution on unhealthy deploy.
- Added health-check retry polling controls (`health_check_retries`, `health_check_interval_seconds`) for watchdog-style validation before rollback.
- Added restart-watchdog polling controls (`restart_watchdog_retries`, `restart_watchdog_interval_seconds`) to validate runtime stability after deploy.
- Added rollback-on-restart-watchdog-failure path and surfaced `restart_watchdog_status` in `SelfBootstrapResult` / API response schema.
- Restart-watchdog flow now accepts typed diagnostics (`RestartWatchdogSignal`) and surfaces `restart_watchdog_reason` in manager and API responses.
- Wired baseline live adapters in `src/att/api/deps.py`:
  - CI status parsing from `gh run list` output
  - PR creation via `gh pr create`
  - PR merge via `gh pr merge`
  - Deploy execution via `DeployManager.run`
  - Restart watchdog diagnostics via `RuntimeManager.probe_health`
  - Rollback execution via `RuntimeManager.stop`
- Added parser helper module `src/att/core/self_bootstrap_integrations.py` with unit tests.
- Added API route: `POST /api/v1/projects/{project_id}/self-bootstrap/run`.
- Added unit coverage in `tests/unit/test_self_bootstrap_manager.py` and integration coverage in `tests/integration/test_api_self_bootstrap.py`.
