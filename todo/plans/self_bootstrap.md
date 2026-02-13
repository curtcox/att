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
- Added baseline release-aware rollback metadata:
  - Request fields: `requested_release_id`, `previous_release_id`, `rollback_release_id`
  - Result/API fields: `deployed_release_id`, `rollback_target_release_id`
  - Rollback executor now supports release-target-aware invocation with backwards-compatible fallback for legacy two-argument executors.
- Added release-source integration for rollback metadata:
  - `SelfBootstrapManager` now accepts `release_metadata_provider` and resolves release metadata when request fields are omitted.
  - Default API dependency wiring resolves release metadata from git (`HEAD` and `HEAD^`) and exposes `release_metadata_source` in self-bootstrap results.
- Added release-source adapter abstraction and fallback chain:
  - `SelfBootstrapManager` now supports `ReleaseSourceAdapter` with `ReleaseSourceContext` for deployment-aware metadata lookup.
  - legacy `release_metadata_provider` hooks remain supported through an internal compatibility adapter.
  - API deps now attempt runtime log release extraction first (`release_id`/`previous_release_id`), then fallback to git metadata.
- Added rollback policy gates and validation outcomes:
  - rollback now evaluates allow/deny policy before executor invocation (`rollback_executor_missing`, `rollback_target_same_as_deployed`, etc.).
  - validation outcomes are surfaced through `rollback_policy_status`, `rollback_policy_reason`, and `rollback_target_valid`.
  - policy outcomes are also recorded in error events for denied rollback attempts.
- Added rollback policy matrix controls by failure class and deployment context:
  - request overrides: `rollback_on_deploy_failure`, `rollback_on_restart_watchdog_failure`, `rollback_on_health_failure`
  - deployment context gate: `deployment_context` (`self_hosted`/`external`) with external target requirement enforcement.
  - result diagnostics now include `rollback_failure_class` and `rollback_deployment_context`.
- Remaining scope before completion:
  - Integrate production deployment registry release-source adapter(s) beyond runtime logs/git fallback.
  - Add additional safe-mode and rollout guardrails for production self-updates.
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
