# Next Machine Handoff

## Snapshot
- Date: 2026-02-12
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: clean
- Validation status:
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`110 passed`)

## Recent Delivered Work
- Runtime logs are manager-backed end-to-end:
  - API: `GET /api/v1/projects/{id}/runtime/logs`
  - MCP tool: `att.runtime.logs`
  - MCP resource: `att://project/{id}/logs`
- `RuntimeManager` now captures subprocess stdout/stderr with bounded in-memory log buffering.
- `TestRunner` upgraded with:
  - summary metrics (`passed/failed/skipped/errors/xfailed/xpassed`)
  - `duration_seconds`
  - `no_tests_collected`
  - timeout handling (`timed_out`, return code `124`)
  - parser helpers for pytest console/json/xml summaries
- API/MCP test surfaces now accept optional marker/timeout controls and return enriched payloads.
- Planning docs already updated for these slices:
  - `todo/master_plan.md`
  - `todo/plans/runtime_manager.md`
  - `todo/plans/test_runner.md`
  - `todo/plans/openapi_routes.md`
  - `todo/plans/mcp_server.md`

## Active Next Slice (Recommended)
Focus next on `P07 runtime_manager` remaining scope (see `todo/plans/runtime_manager.md`):
1. Add runtime health probing beyond process alive/dead.
2. Add restart diagnostics/health signals usable by self-bootstrap watchdog flow.

Suggested implementation direction:
- Extend `RuntimeManager` with explicit health probe API and probe result model.
- Prefer deterministic local checks first (process state + optional health command/http probe when configured).
- Wire health signal into:
  - runtime API route(s) (if exposed)
  - self-bootstrap restart watchdog adapter in `src/att/api/deps.py`
- Add unit tests for healthy/unhealthy/transient probe behavior.
- Update plan docs after each completed step.

## Resume Checklist
1. Sync and verify environment:
   - `git pull`
   - `./.venv313/bin/python --version`
2. Read context docs:
   - `todo/master_plan.md`
   - `todo/plans/runtime_manager.md`
   - `todo/plans/self_bootstrap.md`
   - `todo/plans/mcp_server.md`
3. Implement one slice end-to-end (code + tests + plan updates).
4. Run validation:
   - `./.venv313/bin/ruff format .`
   - `./.venv313/bin/ruff check .`
   - `PYTHONPATH=src ./.venv313/bin/mypy`
   - `PYTHONPATH=src ./.venv313/bin/pytest`
5. Record new state back into this file and `todo/master_plan.md`.

## Key Files for Next Slice
- `src/att/core/runtime_manager.py`
- `src/att/api/routes/runtime.py`
- `src/att/api/deps.py`
- `src/att/core/self_bootstrap_manager.py`
- `tests/unit/test_runtime_manager.py`
- `tests/unit/test_self_bootstrap_manager.py`
- `tests/integration/test_api_self_bootstrap.py`

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (production-grade health probing and release-aware rollback strategy remain).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
