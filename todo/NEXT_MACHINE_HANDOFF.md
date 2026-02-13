# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (uncommitted runtime streaming + self-bootstrap release-aware rollback increments)
- Validation status:
  - `git pull` => `Already up to date.`
  - Full project toolchain (`./.venv313/bin/ruff|mypy|pytest`) is still unavailable in this workspace.
  - Recreating `.venv313` with `uv venv --python 3.13` is blocked by restricted DNS/network for Python download.
  - Fallback syntax validation passed using `python3 -m compileall` on changed source/test files.

## Recent Delivered Work
- Runtime health probes are manager-backed and surfaced end-to-end:
  - `RuntimeManager.probe_health()` in `src/att/core/runtime_manager.py`
  - API runtime status diagnostics (`GET /api/v1/projects/{id}/runtime/status`)
  - MCP runtime status diagnostics (`att.runtime.status`)
- Runtime log streaming now supports cursor-based incremental reads:
  - `RuntimeManager.read_logs(cursor=..., limit=...)` metadata: `cursor/start_cursor/end_cursor/truncated/has_more`
  - API: `GET /api/v1/projects/{id}/runtime/logs` supports optional `cursor`/`limit`
  - MCP tool: `att.runtime.logs` supports optional `cursor`/`limit`
  - MCP resource: `att://project/{id}/logs?cursor=...&limit=...`
- Self-bootstrap restart watchdog diagnostics and baseline release-aware rollback metadata:
  - `RestartWatchdogSignal` + `restart_watchdog_reason`
  - request fields: `requested_release_id`, `previous_release_id`, `rollback_release_id`
  - result fields: `deployed_release_id`, `rollback_target_release_id`
  - rollback executor path supports release-aware invocation with fallback to legacy two-arg executors
- Test coverage updates:
  - `tests/unit/test_runtime_manager.py`
  - `tests/unit/test_runtime_tools.py`
  - `tests/unit/test_resource_refs.py`
  - `tests/integration/test_api_feature_endpoints.py`
  - `tests/integration/test_mcp_transport.py`
  - `tests/unit/test_self_bootstrap_manager.py`
  - `tests/integration/test_api_self_bootstrap.py`
- Planning docs updated:
  - `todo/master_plan.md`
  - `todo/plans/runtime_manager.md`
  - `todo/plans/self_bootstrap.md`

## Active Next Slice (Recommended)
Focus next on `P16 self_bootstrap` hardening beyond request-provided release metadata:
1. Integrate release metadata from concrete deploy/release sources.
2. Harden rollback decision policy using release source of truth and explicit failure semantics.

Suggested implementation direction:
- Introduce a deploy/release signal model (e.g. deployed release, previous stable release, rollout status).
- Update deploy + rollback adapters in `src/att/api/deps.py` to produce/use that model.
- Gate rollback execution on validated release targets (avoid no-op or unknown targets).
- Add unit and integration tests for release-source-driven rollback branches.

## Resume Checklist
1. Sync and verify environment:
   - `git pull`
   - `python3 --version`
2. Restore project toolchain when possible:
   - provide a working `.venv313` (Python 3.13) and install dev dependencies
3. Read context docs:
   - `todo/master_plan.md`
   - `todo/plans/runtime_manager.md`
   - `todo/plans/self_bootstrap.md`
4. Implement one slice end-to-end (code + tests + plan updates).
5. Run validation when toolchain is restored:
   - `./.venv313/bin/ruff format .`
   - `./.venv313/bin/ruff check .`
   - `PYTHONPATH=src ./.venv313/bin/mypy`
   - `PYTHONPATH=src ./.venv313/bin/pytest`
6. Record new state back into this file and `todo/master_plan.md`.

## Key Files for Next Slice
- `src/att/core/self_bootstrap_manager.py`
- `src/att/api/deps.py`
- `src/att/core/deploy_manager.py`
- `src/att/api/routes/self_bootstrap.py`
- `src/att/api/schemas/self_bootstrap.py`
- `tests/unit/test_self_bootstrap_manager.py`
- `tests/integration/test_api_self_bootstrap.py`

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (runtime health/log stream + baseline release-aware rollback metadata done; remaining work is release-source integration and rollback policy hardening).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
