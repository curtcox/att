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
- Added JSON-RPC invocation methods (`tools/call`, `resources/read`) with fallback across servers and error-based degrade handling.
- Added invocation API endpoints (`/api/v1/mcp/invoke/tool`, `/api/v1/mcp/invoke/resource`) and failover tests.
- Added server inspection/deletion and connection event APIs for operational visibility.
- Added explicit MCP initialize handshake support in `MCPClientManager` (`initialize_server`, `initialize_all`) with persisted initialization metadata per server.
- Added initialization API endpoints:
  - `POST /api/v1/mcp/servers/{name}/initialize`
  - `POST /api/v1/mcp/servers/initialize`
- Expanded unit/integration tests for handshake success/failure and initialization endpoint behavior.
