# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (session identity/recovery semantics + adapter capability visibility slice + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`156 passed`)

## Recent Delivered Work
- Added deterministic session identity/recovery coverage:
  - forced refresh now verified to produce a new underlying adapter session identity (not reusing prior session object).
  - transport-level disconnect/timeout invalidation now verified to recreate session state on subsequent invocation.
- Added operator visibility for adapter control capability:
  - `MCPServerResponse` now includes `adapter_controls_available`.
  - `MCPServersResponse` now includes top-level `adapter_controls_available`.
  - allows clients/operators to gate lifecycle controls without trial-and-error `409` probes.
- Expanded tests:
  - unit tests for refresh identity replacement and post-disconnect auto-recreation semantics.
  - integration tests for session-id change across refresh and capability-visibility flags under both NAT-control and non-NAT-control paths.

## Active Next Slice (Recommended)
Continue `P12/P13` with external transport realism and convergence:
1. Add a lightweight adapter diagnostics endpoint for fleet-level operations:
   - e.g. aggregated per-server adapter-session status without requiring per-server `GET` loops.
2. Add targeted resilience coverage for partial cluster operations:
   - invalidate/refresh one server in a multi-server pool and verify failover ordering + event correlation remains deterministic.

Suggested implementation direction:
- Keep manager as single aggregation point; avoid exposing adapter internals in routes.
- Add manager reader method(s) for summarized adapter diagnostics and map through one new route/schema.
- Extend existing fallback tests rather than creating new transport scaffolding.

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
