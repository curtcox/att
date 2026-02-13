# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (MCP capability-snapshot hardening + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`129 passed`)

## Recent Delivered Work
- MCP client lifecycle hardening delivered for `P13`:
  - added explicit per-server capability snapshots in `MCPClientManager`:
    - new `CapabilitySnapshot` model
    - persisted on `ExternalServer.capability_snapshot`
    - captured on successful `initialize` handshake with `protocolVersion`, `serverInfo`, and `capabilities`
  - snapshots are retained across later initialize failures, preserving last-known capability context during partial initialization states.
- MCP API surface expanded:
  - `MCPServerResponse` now includes optional `capability_snapshot` payload.
  - route mapping in `src/att/api/routes/mcp.py` now exposes snapshot metadata.
- Tests expanded:
  - unit tests for snapshot capture + retention after forced initialize failure.
  - integration tests for `initialize`/`connect` endpoints asserting snapshot presence.

## Active Next Slice (Recommended)
Continue `P12/P13` transport hardening with deterministic partial-failure behavior:
1. Add explicit invocation-attempt traces per server (initialize + call outcome) in `MCPInvocationError` details.
2. Tighten API error payload mapping for partial multi-server failures (deterministic machine-readable structure).

Suggested implementation direction:
- Extend `MCPInvocationResult`/`MCPInvocationError` with structured attempt diagnostics.
- Add route-level response model fields for invocation failures (while preserving 503 status).
- Expand integration tests to validate degraded + recovering server sequences and error payload shape.

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
