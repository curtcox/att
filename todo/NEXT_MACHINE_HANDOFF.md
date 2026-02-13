# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (shared MCP test clock helper + stage-paired timeout convergence matrix + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`170 passed`)

## Recent Delivered Work
- Added lightweight manager clock seam for deterministic retry/backoff/freshness behavior in tests:
  - `MCPClientManager` now accepts optional `now_provider` and uses it for retry-window checks, initialization freshness gating, invocation event timestamps, and adapter freshness classification.
  - default behavior remains unchanged (`datetime.now(UTC)` when `now_provider` is not supplied).
  - added unit coverage confirming `should_retry()` consumes injected clock when `now` is omitted.
- Migrated retry-window convergence coverage to clock-driven progression:
  - removed direct `next_retry_at` mutation in the convergence integration scenario; progression now uses `clock.advance(...)` + manager APIs (`record_check_result`).
  - retained deterministic failover/recovery assertions across timeout, retry-window skip, unreachable transition, and recovery initialize.
  - preserved correlation/event determinism checks and freshness assertions after recovery.
- Expanded clock-seam adoption in remaining mixed-state tests:
  - unit and integration mixed-state recovery/fallback tests now use injected test clocks for retry-window progression instead of direct retry-window state mutation.
  - retained existing preferred-order fallback and status-transition assertions while reducing coupling to server internals.
- Extended convergence matrix with clock-driven capability snapshot timing assertions:
  - convergence scenario now explicitly verifies server-local `capability_snapshot.captured_at` retention on failure paths and replacement on recovery initialize.
  - assertions remain request-correlated and deterministic under controlled clock progression.
- Consolidated duplicated MCP test clock helpers into shared support:
  - added shared helper module `tests/support/mcp_helpers.py` and converted unit/integration MCP tests to consume `MCPTestClock`.
  - added package markers (`tests/__init__.py`, `tests/support/__init__.py`) so shared test support imports resolve consistently.
- Expanded stage-specific timeout convergence matrix with explicit paired scenarios:
  - replaced single mixed-stage convergence path with paired `initialize` vs `invoke` timeout scenarios under the same clock progression and preferred order.
  - assertions now explicitly capture stage-specific retry/backoff/status deltas and capability snapshot timing behavior (retention vs replacement) while preserving deterministic correlation/event checks.

## Active Next Slice (Recommended)
Continue `P12/P13` with external transport realism and convergence:
1. Reduce duplicated MCP test scaffolding beyond clocks:
   - extract shared cluster NAT session factory/session model helpers used in integration MCP tests into `tests/support` to shrink repeated test-local transport setup.
   - keep behavior unchanged while improving test readability and maintenance.
2. Extend stage-paired convergence coverage with diagnostics filter assertions:
   - for each timeout stage, assert deterministic event-filter behavior (`server`, `request_id`, `correlation_id`, `limit`) on both `/api/v1/mcp/events` and `/api/v1/mcp/invocation-events`.
   - preserve server-local capability snapshot timing assertions and preferred-order fallback determinism.

Suggested implementation direction:
- Keep manager as aggregation/source-of-truth and route logic thin.
- Reuse existing fake NAT session factories and extend existing clock helper usage rather than adding new transport scaffolding.
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
