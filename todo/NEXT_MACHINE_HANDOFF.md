# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (adapter diagnostics query controls + mixed-state invalidate-one-server coverage + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`162 passed`)

## Recent Delivered Work
- Expanded aggregated adapter diagnostics controls:
  - `GET /api/v1/mcp/adapter-sessions` now supports query controls: `server`, `active_only`, and `limit`.
  - `MCPClientManager.list_adapter_sessions()` now supports matching manager-level filtering/limit semantics as source-of-truth.
  - added unit and integration coverage for filter/limit behavior while preserving deterministic ordering.
- Added deeper mixed-state invalidate coverage:
  - new integration scenario invalidates `primary` while `backup` remains active.
  - verifies unaffected `backup` session identity remains stable and `capability_snapshot` is unchanged across subsequent invokes.
  - validates aggregated adapter diagnostics reflect `primary` inactive and `backup` active after targeted invalidation.

## Active Next Slice (Recommended)
Continue `P12/P13` with external transport realism and convergence:
1. Add lightweight adapter-session health semantics to diagnostics:
   - classify/surface session freshness (e.g., unknown/stale/active-recent) without exposing sensitive transport state.
   - keep manager as source-of-truth and expose semantics through `GET /api/v1/mcp/adapter-sessions` and per-server adapter payloads.
2. Expand mixed-state cluster coverage beyond single invalidation:
   - combine refresh + invalidate + induced timeout across different servers and verify deterministic fallback order and correlation IDs remain stable.
   - assert capability snapshot retention/replacement rules stay server-local under mixed transitions.

Suggested implementation direction:
- Keep manager as aggregation/source-of-truth and route logic thin.
- Reuse existing fake NAT session factories and extend with server-specific freshness/identity assertions to avoid new transport scaffolding.
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
