# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (MCP event correlation/filter slice + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`143 passed`)

## Recent Delivered Work
- Added cross-event correlation linkage between invocation lifecycle and connection transitions:
  - `ConnectionEvent` now carries optional `correlation_id`.
  - invocation-triggered health/status updates now propagate the invocation `request_id` as `correlation_id`.
  - initialize/invoke failures and recoveries during `_invoke()` now produce connection transitions that can be traced to lifecycle events.
- Added manager-side event query/filter controls:
  - `list_events(server=..., correlation_id=..., limit=...)`
  - `list_invocation_events(server=..., method=..., request_id=..., limit=...)`
  - limit semantics are deterministic and bounded to most-recent matching records.
- Added API query/filter controls:
  - `GET /api/v1/mcp/events` supports `server`, `correlation_id`, `limit`.
  - `GET /api/v1/mcp/invocation-events` supports `server`, `method`, `request_id`, `limit`.
  - connection event payload schema now includes `correlation_id`.
- Added coverage for correlation and filters:
  - unit tests for manager-level correlation/filter/limit behavior.
  - integration tests for endpoint filter semantics and correlation consistency.

## Active Next Slice (Recommended)
Continue `P12/P13` with external transport realism and convergence:
1. Introduce a production-facing `nat.mcp` transport adapter path behind `MCPClientManager` (while preserving current HTTP JSON-RPC fallback for tests/local).
2. Add adapter-focused tests covering:
   - initialization + invoke happy path
   - timeout/HTTP/malformed response category mapping parity
   - fallback sequencing across mixed healthy/degraded servers when adapter calls fail

Suggested implementation direction:
- Keep protocol normalization in the manager (`JSONObject` contract + category mapping), with adapter-specific translation isolated to transport boundaries.
- Start with dependency-injected adapter callable (parallel to current `MCPTransport` protocol) to avoid broad route/API churn.
- Expand `tests/unit/test_mcp_client.py` first, then add one focused integration case in `tests/integration/test_api_mcp.py`.

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
