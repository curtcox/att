# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (MCP stale-initialization/recovery hardening + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`135 passed`)

## Recent Delivered Work
- MCP stale-initialization and recovery sequencing hardening delivered (`P13`):
  - added initialization freshness metadata to servers:
    - `initialization_expires_at`
  - `MCPClientManager` now supports staleness gating via `max_initialization_age_seconds` and forces reinitialize before invocation when initialization is stale.
  - unhealthy transitions now invalidate initialization expiry metadata.
- API surface updated:
  - MCP server payload now includes `initialization_expires_at` in `MCPServerResponse`.
- Test coverage expanded:
  - unit test validates stale initialized server is reinitialized before invocation.
  - unit/integration tests validate deterministic mixed-state recovery order (`healthy` -> fallback to `recovered`, while skipping unnecessary degraded attempts after recovery succeeds).

## Active Next Slice (Recommended)
Continue `P12/P13` transport hardening with live external-server realism:
1. Add explicit transport-classified failure reasons (network timeout vs HTTP status vs malformed payload) and map these into stable server error categories.
2. Extend API/integration coverage for these categories to confirm deterministic status transitions and diagnostic payloads.

Suggested implementation direction:
- Introduce typed transport error classification in `MCPClientManager` (and default transport wrapper) instead of plain string errors.
- Preserve backward-compatible error text while surfacing structured error category fields.
- Add integration tests for malformed JSON-RPC payloads and non-2xx transport responses.

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

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (release-source adapter chain + failure-class/deployment-context rollback policy matrix delivered; remaining work is deeper production rollout hardening).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
