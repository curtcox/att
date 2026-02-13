# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (MCP invocation-error diagnostics hardening + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`131 passed`)

## Recent Delivered Work
- MCP invocation failure diagnostics hardened for `P13`:
  - added `MCPInvocationAttempt` trace model in `MCPClientManager`.
  - `MCPInvocationError` now carries `method` and ordered attempt traces (per server, `initialize`/`invoke`, success/error).
  - invocation failures now preserve deterministic per-candidate diagnostics across fallback sequences.
- MCP API error payload mapping tightened:
  - `/api/v1/mcp/invoke/tool` and `/api/v1/mcp/invoke/resource` now emit structured 503 details:
    - `message`
    - `method`
    - `attempts[]`
  - new error detail schemas added in `src/att/api/schemas/mcp.py`.
- Test coverage expanded:
  - unit tests validate `MCPInvocationError` method + attempt traces for no-server and partial-failure scenarios.
  - integration tests validate 503 detail payload structure and attempt traces.

## Active Next Slice (Recommended)
Continue `P12/P13` transport hardening with recovery-focused sequencing:
1. Add explicit "stale initialization" handling and forced re-initialize rules for degraded/recovered servers before invocation.
2. Expand integration tests for mixed-state clusters (healthy + degraded + recovered) to verify deterministic server selection and status transitions.

Suggested implementation direction:
- Add initialization freshness metadata and reinitialize gating in `MCPClientManager`.
- Ensure recovered servers can re-enter healthy rotation predictably after transient failures.
- Add API tests that exercise multi-step recoveries and assert stable payload shape + transition events.

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
