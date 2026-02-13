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
- Added cross-event correlation and diagnostics filtering controls:
  - connection transition events now include optional `correlation_id` for linking transitions to invocation lifecycle `request_id`.
  - manager readers now support deterministic filter/limit queries for both streams (`server`, `method`, `request_id`, `correlation_id`, `limit`).
  - API diagnostics endpoints now expose query controls for focused retrieval without route-level post-filtering.
  - unit/integration coverage verifies correlation consistency and filter/limit semantics.
- Added NAT MCP transport adapter path with fallback-safe dependency wiring:
  - introduced `NATMCPTransportAdapter` for streamable-HTTP session-backed MCP request dispatch (`initialize`, `notifications/initialized`, `tools/call`, `resources/read`).
  - `MCPClientManager` now supports adapter-first transport resolution (`transport_adapter` then legacy/custom transport then default HTTP transport).
  - added `create_nat_mcp_transport_adapter()` for optional SDK-backed adapter construction in API deps without breaking local/test fallback behavior.
  - expanded unit/integration tests for adapter happy path, timeout/http-status/malformed category parity, and mixed-state failover sequencing when adapter calls fail.
- Added adapter lifecycle controls + diagnostics surfaces:
  - manager-level controls for adapter-backed sessions (`supports_adapter_session_controls`, `adapter_session_diagnostics`, `invalidate_adapter_session`, `refresh_adapter_session`).
  - adapter-level diagnostics include non-sensitive `active`, `initialized`, and `last_activity_at`.
  - API server payloads now include `adapter_session` metadata and expose explicit lifecycle endpoints:
    - `POST /api/v1/mcp/servers/{name}/adapter/invalidate`
    - `POST /api/v1/mcp/servers/{name}/adapter/refresh`
  - endpoints return `409` when lifecycle controls are unavailable (non-NAT adapter path), with integration coverage.
- Added explicit recovery-semantics and capability-visibility coverage:
  - refresh now validated to recreate underlying adapter session identity (new session instance) rather than reusing stale state.
  - transport-triggered invalidation (e.g., timeout/disconnect category) now validated to recreate session on next invocation.
  - MCP server/list payloads now expose `adapter_controls_available` so clients can gate lifecycle operations without probing for `409`.
- Added aggregated adapter diagnostics and partial-cluster resilience coverage:
  - manager now exposes aggregated adapter session status across registered servers (`list_adapter_sessions`).
  - new API endpoint `GET /api/v1/mcp/adapter-sessions` returns fleet-level per-server adapter diagnostics plus control-capability status.
  - integration coverage validates deterministic fallback ordering and correlation linkage when refreshing one server in a mixed cluster and then inducing partial failure.
- Expanded aggregated adapter diagnostics controls:
  - `list_adapter_sessions` now supports source-of-truth filtering and limiting (`server_name`, `active_only`, `limit`).
  - `GET /api/v1/mcp/adapter-sessions` now exposes matching query controls (`server`, `active_only`, `limit`) with deterministic server ordering.
  - unit/integration coverage validates active-only filtering, single-server filtering, and deterministic tail-limit semantics.
- Added mixed-state invalidate isolation coverage:
  - integration test invalidates one server adapter session (`primary`) while confirming unaffected peer (`backup`) remains active and preferred.
  - verifies unaffected server session identity remains stable and capability snapshot metadata is unchanged through subsequent invokes.
- Added lightweight adapter-session freshness semantics:
  - manager now classifies adapter diagnostics freshness as `unknown`, `active_recent`, or `stale` using a configurable stale window (`adapter_session_stale_after_seconds`).
  - per-server API payloads (`adapter_session`) and aggregated API payloads (`GET /api/v1/mcp/adapter-sessions`) now surface freshness consistently from manager source-of-truth.
  - unit/integration tests cover unknown->active_recent->stale transitions and stale-state visibility via both endpoints.
- Added mixed-state refresh/invalidate/timeout convergence coverage:
  - integration scenario combines `refresh(primary)`, `invalidate(backup)`, then induced `network_timeout` on primary invoke.
  - validates deterministic failover ordering/correlation linkage and timeout category mapping.
  - asserts capability snapshot replacement/retention remains server-local across mixed transitions while adapter session diagnostics reflect expected active/freshness state.
- Expanded adapter diagnostics freshness query controls:
  - `list_adapter_sessions` now supports `freshness` filtering (`unknown`, `active_recent`, `stale`) alongside existing `server`/`active_only`/`limit` filters.
  - `GET /api/v1/mcp/adapter-sessions` now accepts `freshness` and delegates filtering to manager source-of-truth.
  - integration coverage asserts freshness-filtered aggregation remains consistent with per-server `/api/v1/mcp/servers` diagnostics.
- Added retry-window convergence coverage across consecutive recovery cycles:
  - integration scenario now exercises timeout -> retry-window skip -> retry-window expiry -> unreachable transition -> recovery initialize.
  - coverage includes initialize-time timeout stage to validate degraded/unreachable progression semantics independently from invoke-time timeout semantics.
  - correlation/invocation event assertions remain deterministic per request across the full cycle sequence.
- Added deterministic clock seam for MCP client manager timing:
  - `MCPClientManager` now accepts optional `now_provider` used by retry-window checks, invocation event timestamps, initialization freshness gating, and adapter freshness classification.
  - preserves runtime defaults while enabling deterministic test-time progression.
  - added unit test coverage for `should_retry()` under injected clock.
- Migrated convergence scenario timing control from internal-state mutation to clock progression:
  - retry-window advancement now uses clock increments plus manager APIs rather than direct `next_retry_at` assignment.
  - keeps degraded/unreachable/recovered transition assertions while reducing test coupling to server internals.
- Expanded clock progression usage across remaining mixed-state tests:
  - unit and integration mixed-state fallback/recovery tests now use injected test clocks and time advancement rather than direct retry-window mutation.
  - preserves preferred-order and status assertions while reducing internal-state coupling.
- Added clock-driven capability snapshot timing assertions in convergence flow:
  - verifies `capability_snapshot.captured_at` remains stable across failure/no-reinitialize paths and updates on recovery initialize.
  - keeps assertions server-local and deterministic per request/correlation cycle.
- Consolidated MCP test clock scaffolding:
  - introduced shared helper `tests/support/mcp_helpers.py` with `MCPTestClock`.
  - migrated unit/integration MCP test modules to shared clock helper to eliminate duplicated local clock definitions.
- Expanded convergence matrix to explicit stage-paired scenarios:
  - convergence coverage now runs paired `initialize`-timeout and `invoke`-timeout scenarios under the same clock progression and preferred ordering.
  - assertions explicitly verify stage-specific retry/backoff/status outcomes and capability snapshot timing deltas while preserving deterministic event/correlation checks.
