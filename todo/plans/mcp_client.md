# P13 - mcp_client

## Status
in_progress

## Phase
1.2

## Dependencies
P11

## Scope
- Define concrete implementation tasks.
- Define required tests and acceptance criteria.
- Track delivery notes and unresolved risks.

## Acceptance Criteria
- The implementation is merged with passing CI checks.
- Tests for this plan item exist and cover baseline behavior.
- `todo/master_plan.md` is updated with completion status.

## Notes
- Implemented health/backoff-aware MCP client manager in `src/att/mcp/client.py`.
- Added retry policy, degraded/unreachable states, transition events, and server selection logic.
- Added unit coverage in `tests/unit/test_mcp_client.py`.
- Added API management endpoints and integration tests in `tests/integration/test_api_mcp.py`.
