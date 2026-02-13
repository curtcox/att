# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (uncommitted runtime health probe + watchdog diagnostics slice)
- Validation status:
  - `git pull` => `Already up to date.`
  - Handoff toolchain path `./.venv313/bin/...` is not present in this workspace.
  - Attempts to recreate `.venv313` with `uv venv --python 3.13` failed due restricted DNS/network access for Python downloads.
  - Fallback syntax validation passed: `python3 -m compileall src tests`.

## Recent Delivered Work
- Added typed runtime health probe model and API in `src/att/core/runtime_manager.py`:
  - `RuntimeHealthProbe`
  - `RuntimeManager.probe_health(...)`
  - supports process-state probe plus optional configured HTTP/command probes.
- Runtime status surfaces now return health diagnostics:
  - API: `GET /api/v1/projects/{id}/runtime/status`
  - MCP tool path: `att.runtime.status`
- Self-bootstrap restart watchdog now consumes runtime probe signals and surfaces diagnostics:
  - new `RestartWatchdogSignal` support
  - `restart_watchdog_reason` propagated through `SelfBootstrapResult` and API schema/route.
- Added/updated tests for healthy/unhealthy/transient probe behavior and watchdog diagnostics in:
  - `tests/unit/test_runtime_manager.py`
  - `tests/unit/test_self_bootstrap_manager.py`
  - `tests/integration/test_api_feature_endpoints.py`
  - `tests/integration/test_api_self_bootstrap.py`
- Planning docs updated:
  - `todo/master_plan.md`
  - `todo/plans/runtime_manager.md`
  - `todo/plans/self_bootstrap.md`

## Active Next Slice (Recommended)
Focus next on closing remaining `P07 runtime_manager` scope and continuing `P16` hardening:
1. Implement streaming runtime log delivery semantics for long-running sessions.
2. Continue release-aware rollback strategy hardening in self-bootstrap (`P16`).

Suggested implementation direction:
- Add incremental log cursor/offset semantics to runtime log reads (API + MCP).
- Preserve bounded in-memory buffering while enabling client-side tail/follow patterns.
- Extend self-bootstrap rollback decisioning with release/version context (not only health outcome).
- Add tests for log streaming pagination/tail behavior and rollback decision branches.

## Resume Checklist
1. Sync and verify environment:
   - `git pull`
   - `python3 --version`
2. Restore test/lint toolchain (blocked in this snapshot):
   - recreate `.venv313` when network access is available (or provide an existing local 3.13 venv)
   - install dev deps from `pyproject.toml`
3. Read context docs:
   - `todo/master_plan.md`
   - `todo/plans/runtime_manager.md`
   - `todo/plans/self_bootstrap.md`
4. Implement one slice end-to-end (code + tests + plan updates).
5. Run validation:
   - `./.venv313/bin/ruff format .`
   - `./.venv313/bin/ruff check .`
   - `PYTHONPATH=src ./.venv313/bin/mypy`
   - `PYTHONPATH=src ./.venv313/bin/pytest`
6. Record new state back into this file and `todo/master_plan.md`.

## Key Files for Next Slice
- `src/att/core/runtime_manager.py`
- `src/att/api/routes/runtime.py`
- `src/att/api/routes/mcp_transport.py`
- `src/att/core/self_bootstrap_manager.py`
- `src/att/api/deps.py`
- `tests/unit/test_runtime_manager.py`
- `tests/unit/test_self_bootstrap_manager.py`
- `tests/integration/test_api_feature_endpoints.py`
- `tests/integration/test_api_self_bootstrap.py`

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (runtime-health diagnostics integrated; remaining work is release-aware rollback hardening).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
