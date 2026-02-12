# P07 - runtime_manager

## Status
in_progress

## Phase
0.4

## Dependencies
P03,P04

## Scope
- Define concrete implementation tasks.
- Define required tests and acceptance criteria.
- Track delivery notes and unresolved risks.

## Acceptance Criteria
- The implementation is merged with passing CI checks.
- Tests for this plan item exist and cover baseline behavior.
- `todo/master_plan.md` is updated with completion status.

## Notes
- Implemented subprocess lifecycle methods in `src/att/core/runtime_manager.py`: `start`, `stop`, and `status` for a single managed runtime process.
- Added bounded in-memory runtime log buffering (`max_log_lines`) with background stdout drain thread so process output is captured while running.
- Added `RuntimeManager.logs(limit=...)` and wired log reads through API route `GET /api/v1/projects/{id}/runtime/logs`.
- Wired MCP runtime log reads to manager-backed logs for both `att.runtime.logs` and resource reads via `att://project/{id}/logs`.
- Added coverage in:
  - `tests/unit/test_runtime_manager.py`
  - `tests/integration/test_api_feature_endpoints.py`
  - `tests/integration/test_mcp_transport.py`
- Remaining scope before completion:
  - Runtime health probing beyond process alive/dead status.
  - Streaming runtime log delivery semantics for long-running sessions.
