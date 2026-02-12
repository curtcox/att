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
- Project routes now include clone/download endpoints in addition to CRUD.
- Added MCP management/discovery routes (`/api/v1/mcp/*`) and MCP transport route (`POST /mcp`) for JSON-RPC-style tool/resource access.
- MCP management surface now includes explicit server initialization routes (`/api/v1/mcp/servers/{name}/initialize`, `/api/v1/mcp/servers/initialize`).
- MCP management surface now also includes combined connect routes (`/api/v1/mcp/servers/{name}/connect`, `/api/v1/mcp/servers/connect`).
- Runtime logs route now returns manager-backed process output via `RuntimeManager.logs()` (`GET /api/v1/projects/{id}/runtime/logs`).
- Integration coverage includes feature endpoint tests and MCP-specific API tests in `tests/integration/`.
