# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (adapter session freshness semantics + mixed-state refresh/invalidate/timeout coverage + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`165 passed`)

## Recent Delivered Work
- Added lightweight adapter-session freshness semantics at manager/source-of-truth:
  - new freshness classification (`unknown`, `active_recent`, `stale`) for adapter diagnostics.
  - surfaced through per-server payloads (`adapter_session`) and fleet aggregation (`GET /api/v1/mcp/adapter-sessions`).
  - stale-window control added to `MCPClientManager` (`adapter_session_stale_after_seconds`), with tests covering unknown/recent/stale transitions.
- Expanded mixed-state cluster resilience coverage:
  - new integration scenario combines `refresh(primary)` + `invalidate(backup)` + induced timeout on `primary`.
  - verifies deterministic failover ordering, request-level correlation linkage, timeout categorization, and server-local capability snapshot retention/replacement behavior.
  - validates resulting adapter freshness and active-state diagnostics after mixed transitions.

## Active Next Slice (Recommended)
Continue `P12/P13` with external transport realism and convergence:
1. Add freshness-aware diagnostics query controls:
   - extend `GET /api/v1/mcp/adapter-sessions` with optional `freshness` filtering while preserving deterministic ordering and existing filters.
   - add server-list level assertions to ensure per-server and aggregated freshness views remain consistent under filtering.
2. Push transport realism deeper with retry-window convergence:
   - add mixed-state scenario combining timeout -> retry-window expiry -> recovery initialize to validate degraded/unreachable transitions with adapter freshness evolution.
   - assert correlation/event streams remain deterministic across consecutive recovery cycles.

Suggested implementation direction:
- Keep manager as aggregation/source-of-truth and route logic thin.
- Reuse existing fake NAT session factories and extend with freshness + retry-window assertions to avoid new transport scaffolding.
- Preserve current event/filter semantics and correlation determinism.

## Resume Checklist
1. Sync and verify environment:
   - `git pull`
   - `./.venv313/bin/python --version`
2. Read context docs:
   - `todo/master_plan.md`
   - `todo/plans/mcp_server.md`
   - `todo/plans/mcp_client.md`
3. Implement one slice end-to-end (code + tests + plan updates).
4. Run validation:
   - `./.venv313/bin/ruff format .`
   - `./.venv313/bin/ruff check .`
   - `PYTHONPATH=src ./.venv313/bin/mypy`
   - `PYTHONPATH=src ./.venv313/bin/pytest`
5. Record new state back into this file and `todo/master_plan.md`.

## Key Files for Next Slice
- `src/att/mcp/client.py`
- `src/att/api/routes/mcp.py`
- `src/att/api/schemas/mcp.py`
- `tests/unit/test_mcp_client.py`
- `tests/integration/test_api_mcp.py`
- `src/att/api/deps.py`

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (release-source adapter chain + failure-class/deployment-context rollback policy matrix delivered; remaining work is deeper production rollout hardening).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
