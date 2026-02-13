# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (uncommitted runtime streaming + self-bootstrap rollback hardening increments)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`124 passed`)

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
- Self-bootstrap rollback hardening increments:
  - restart watchdog diagnostics with `RestartWatchdogSignal` + `restart_watchdog_reason`
  - release-aware request/result fields (`requested_release_id`, `previous_release_id`, `rollback_release_id`, `deployed_release_id`, `rollback_target_release_id`)
  - rollback executor path supports both release-aware (3-arg) and legacy (2-arg) callables
  - release metadata source integration: `release_metadata_provider` hook + default git-backed provider (`HEAD`, `HEAD^`) in `src/att/api/deps.py`
  - self-bootstrap response now surfaces `release_metadata_source`
- Local toolchain restored on this machine:
  - created `.venv313` (Python 3.13.12)
  - installed project + dev dependencies (`uv pip install --python .venv313/bin/python -e '.[dev]'`)

## Active Next Slice (Recommended)
Focus next on final `P16 self_bootstrap` hardening:
1. Add rollback policy gates and explicit failure classification.
2. Validate rollback targets before execution and emit deterministic policy outcomes.

Suggested implementation direction:
- Add rollback policy model (e.g., allow/deny with reason codes) inside `SelfBootstrapManager`.
- Validate selected rollback target release before invoking rollback executor.
- Emit policy + validation outcome fields in result/event payloads.
- Extend unit/integration tests for deny/allow branches and invalid target handling.

## Resume Checklist
1. Sync and verify environment:
   - `git pull`
   - `./.venv313/bin/python --version`
2. Read context docs:
   - `todo/master_plan.md`
   - `todo/plans/runtime_manager.md`
   - `todo/plans/self_bootstrap.md`
3. Implement one slice end-to-end (code + tests + plan updates).
4. Run validation:
   - `./.venv313/bin/ruff format .`
   - `./.venv313/bin/ruff check .`
   - `PYTHONPATH=src ./.venv313/bin/mypy`
   - `PYTHONPATH=src ./.venv313/bin/pytest`
5. Record new state back into this file and `todo/master_plan.md`.

## Key Files for Next Slice
- `src/att/core/self_bootstrap_manager.py`
- `src/att/api/deps.py`
- `src/att/api/routes/self_bootstrap.py`
- `src/att/api/schemas/self_bootstrap.py`
- `tests/unit/test_self_bootstrap_manager.py`
- `tests/integration/test_api_self_bootstrap.py`

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (runtime health/log stream + release-source-aware rollback metadata done; remaining work is rollback policy hardening).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
