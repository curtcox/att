# P14 - openapi_routes

## Status
in_progress

## Phase
1.3

## Dependencies
P04-P08,P10

## Scope
- Define concrete implementation tasks.
- Define required tests and acceptance criteria.
- Track delivery notes and unresolved risks.

## Acceptance Criteria
- The implementation is merged with passing CI checks.
- Tests for this plan item exist and cover baseline behavior.
- `todo/master_plan.md` is updated with completion status.

## Notes
- Baseline FastAPI route surface implemented across project/code/git/runtime/test/debug/deploy/workflow/events/self-bootstrap APIs.
- Added MCP management/discovery routes (`/api/v1/mcp/*`) and MCP transport route (`POST /mcp`) for JSON-RPC-style tool/resource access.
- Integration coverage includes feature endpoint tests and MCP-specific API tests in `tests/integration/`.
