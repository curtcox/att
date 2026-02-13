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
- Invocation now auto-initializes candidate servers before `tools/call` / `resources/read`, and falls back to the next server if initialization fails.
- Added combined connect operations in client manager (`connect_server`, `connect_all`) to run health-check + initialize in one step.
- Added connect API endpoints:
  - `POST /api/v1/mcp/servers/{name}/connect`
  - `POST /api/v1/mcp/servers/connect`
- Added explicit per-server capability snapshots captured from successful MCP initialize responses:
  - new manager model `CapabilitySnapshot` persisted on `ExternalServer`.
  - snapshots include `protocol_version`, `server_info`, `capabilities`, and `captured_at`.
  - API server payloads now expose `capability_snapshot` for operational visibility.
- Added test coverage for capability-snapshot lifecycle:
  - snapshot population on initialize success.
  - snapshot retention across later initialize failures (partial initialization state recovery).
- Added structured invocation-attempt diagnostics for failure analysis:
  - `MCPInvocationError` now carries `method` and per-server attempt trace entries (`initialize`/`invoke`, success, error).
  - invocation failures include deterministic attempt ordering across fallback candidates.
- Added deterministic API error payload mapping for invocation failures:
  - `/api/v1/mcp/invoke/tool` and `/api/v1/mcp/invoke/resource` now return structured 503 `detail` payloads with `message`, `method`, and `attempts`.
  - integration coverage validates both no-server and partial-failure trace payload shapes.
- Added initialization freshness metadata and stale reinitialize gating:
  - `ExternalServer` now tracks `initialization_expires_at`.
  - `MCPClientManager` now computes initialization expiry from `max_initialization_age_seconds` and forces reinitialize before invocation when metadata is stale.
  - unhealthy transitions now invalidate initialization expiry.
- Added mixed-state recovery sequencing tests:
  - deterministic preferred-order fallback across `healthy` + `recovered` + `degraded` servers.
  - explicit stale-server reinitialize assertions in both unit and API integration tests.
- Added explicit transport-classified failure categories:
  - `ErrorCategory` classification now tracked on servers (`last_error_category`) and invocation attempts (`error_category`).
  - introduced `MCPTransportError` for category-preserving transport failures.
  - default transport now classifies timeout/http-status/malformed-payload failures into stable categories.
- Added integration coverage for category mapping:
  - invocation 503 detail now includes category-aware attempts.
  - server state payloads expose categorized last error for deterministic diagnostics.
- Added invocation lifecycle event auditing with bounded retention:
  - `MCPClientManager` now records per-server invocation lifecycle events (`initialize_start/success/failure`, `invoke_start/success/failure`).
  - lifecycle events are retained in a bounded in-memory buffer (`max_invocation_events`) and include method/request/server/timestamp/error metadata.
- Added invocation lifecycle API exposure:
  - new endpoint `GET /api/v1/mcp/invocation-events` returns ordered invocation lifecycle records.
  - integration tests assert event ordering/payload stability under fallback and failover scenarios.
