# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (MCP invocation-lifecycle event auditing + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`140 passed`)

## Recent Delivered Work
- MCP invocation lifecycle auditing delivered (`P13`):
  - added bounded in-memory invocation lifecycle event buffer in `MCPClientManager`.
  - per-server lifecycle phases emitted during invocation:
    - `initialize_start`
    - `initialize_success`
    - `initialize_failure`
    - `invoke_start`
    - `invoke_success`
    - `invoke_failure`
  - events include `method`, `request_id`, `server`, `timestamp`, and optional error/category metadata.
- API exposure added:
  - new endpoint `GET /api/v1/mcp/invocation-events`.
  - new response schemas for invocation lifecycle events.
- Existing diagnostics preserved and expanded:
  - category-aware server failures (`last_error_category`) and invocation attempt errors (`error_category`) remain intact.
- Test coverage expanded:
  - unit tests for lifecycle event ordering and retention bounds.
  - integration tests for `/api/v1/mcp/invocation-events` ordering/payload behavior under fallback.

## Active Next Slice (Recommended)
Continue `P12/P13` with external transport realism and convergence:
1. Add invocation lifecycle linkage to existing connection transition events (shared correlation identifiers and cross-event traceability).
2. Extend API diagnostics with filter/query controls (e.g., by server, method, request_id, recent limit) for both connection and invocation event streams.

Suggested implementation direction:
- Add optional event query params in MCP event endpoints with deterministic ordering and limit semantics.
- Add manager-side filtered readers to avoid route-level post-filtering complexity.
- Expand integration tests to validate filter behavior and correlation consistency in mixed-state failover sequences.

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
