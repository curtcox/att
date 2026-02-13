# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (adapter freshness query filtering + retry-window convergence coverage + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`168 passed`)

## Recent Delivered Work
- Expanded adapter diagnostics query controls with freshness filtering:
  - `MCPClientManager.list_adapter_sessions()` now supports `freshness` filtering (`unknown`, `active_recent`, `stale`) in addition to `server`, `active_only`, and `limit`.
  - `GET /api/v1/mcp/adapter-sessions` now accepts `freshness` query input and delegates filtering to manager source-of-truth.
  - added unit/integration coverage for freshness filtering plus consistency assertions between `/servers` per-server diagnostics and aggregated diagnostics.
- Added retry-window convergence coverage across consecutive cycles:
  - new integration scenario validates timeout -> retry-window skip -> retry-window expiry -> unreachable transition -> recovery initialize path.
  - verifies deterministic per-request invocation-event sequences and correlation-linkage behavior across consecutive failover/recovery cycles.
  - asserts adapter freshness visibility remains correct after recovered primary invocation.

## Active Next Slice (Recommended)
Continue `P12/P13` with external transport realism and convergence:
1. Reduce test-only state mutation in convergence coverage:
   - introduce a lightweight clock seam in `MCPClientManager` so retry-window expiry can be tested without mutating server internals (`next_retry_at`) directly.
   - migrate mixed-state retry-window tests to clock-driven progression for clearer invariants.
2. Expand convergence matrix for initialization-vs-invoke timeout classes:
   - add explicit scenario coverage showing retry/backoff/status effects differ when timeout occurs during initialize versus invoke.
   - preserve deterministic correlation/event assertions and server-local capability snapshot behavior.

Suggested implementation direction:
- Keep manager as aggregation/source-of-truth and route logic thin.
- Reuse existing fake NAT session factories and extend with timeout-stage toggles + clock control to avoid new transport scaffolding.
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
