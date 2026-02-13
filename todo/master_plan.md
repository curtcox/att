# ATT (Agent Toolkit Toolkit) Master Plan

## Vision

ATT is a web-based application for developing, running, debugging, and deploying NVIDIA NeMo Agent Toolkit (NAT) apps. It is built on NAT itself, exposes an OpenAPI interface, and functions as both an MCP client and MCP server. The top priority is reaching self-bootstrapping: the point where ATT can create future versions of itself.

## Implementation Progress (2026-02-13)

- [x] Consolidated timeout-category constant naming across scripted and non-scripted failover diagnostics assertions:
  - introduced neutral `FAILOVER_TIMEOUT_ERROR_CATEGORY` and migrated timeout-category assertion call sites away from scripted-only naming.
  - updated focused constant regression coverage to assert neutral timeout-category value plus compatibility-alias equivalence.
  - preserved diagnostics-filter semantics and call-order literal/subsequence behavior unchanged.
- [x] Retired degraded-status compatibility alias debt after canonical ownership migration:
  - removed `SCRIPTED_FAILOVER_DEGRADED_EXPECTED_STATUSES` compatibility alias and retained only canonical `FAILOVER_DEGRADED_EXPECTED_STATUSES` for degraded-status expectations.
  - updated focused constant regression coverage to assert canonical degraded-status vector semantics without alias coupling.
  - preserved diagnostics-filter semantics and call-order literal/subsequence behavior unchanged.
- [x] Canonicalized degraded-status constant ownership after alias adoption in MCP integration diagnostics tests:
  - made `FAILOVER_DEGRADED_EXPECTED_STATUSES` the literal-defined canonical degraded-status tuple.
  - kept `SCRIPTED_FAILOVER_DEGRADED_EXPECTED_STATUSES` as a compatibility alias to the canonical constant and updated focused regression coverage to assert canonical-vector and alias-equivalence semantics.
  - preserved diagnostics-filter semantics and call-order literal/subsequence behavior unchanged.
- [x] Consolidated degraded-status constant naming across scripted and non-scripted failover diagnostics assertions:
  - migrated remaining scripted failover `expected_statuses` call sites from `list(SCRIPTED_FAILOVER_DEGRADED_EXPECTED_STATUSES)` to `list(FAILOVER_DEGRADED_EXPECTED_STATUSES)` for consistent assertion wiring.
  - kept scripted constant regression coverage and added explicit alias parity assertion (`FAILOVER_DEGRADED_EXPECTED_STATUSES == SCRIPTED_FAILOVER_DEGRADED_EXPECTED_STATUSES`) to lock semantic equivalence.
  - preserved diagnostics-filter semantics and call-order literal/subsequence behavior unchanged.
- [x] Reduced final duplicated degraded-status vectors in non-scripted diagnostics assertions:
  - introduced neutral constant alias `FAILOVER_DEGRADED_EXPECTED_STATUSES` in `tests/integration/test_api_mcp.py` so generic degraded-status checks no longer depend on scripted-specific naming.
  - replaced non-scripted event-endpoint and resource failover/recovery `expected_statuses=[ServerStatus.DEGRADED.value]` vectors with `list(FAILOVER_DEGRADED_EXPECTED_STATUSES)`.
  - eliminated remaining inline degraded-status vectors in `tests/integration/test_api_mcp.py` while preserving diagnostics-filter and call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated degraded-status vectors in remaining scripted failover diagnostics assertions (outside stage-paired and transport-error tests):
  - replaced scripted failover `expected_statuses=[ServerStatus.DEGRADED.value]` vectors in initialize/invoke isolation, initialize-script exhaustion fallback, and scripted initialize-precedence tool/resource tests with `list(SCRIPTED_FAILOVER_DEGRADED_EXPECTED_STATUSES)`.
  - kept diagnostics-filter and call-order assertions explicit at each test call site while reusing the shared degraded-status constant.
  - preserved invocation/connection filter semantics and call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated degraded-status vectors in scripted transport-error failover diagnostics assertions:
  - replaced scripted transport-error failover `expected_statuses=[ServerStatus.DEGRADED.value]` vectors in both tool/resource error-action tests with `list(SCRIPTED_FAILOVER_DEGRADED_EXPECTED_STATUSES)`.
  - kept diagnostics-filter and call-order assertions explicit at each test call site while reusing the shared degraded-status constant.
  - preserved invocation/connection filter semantics and call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated degraded-status vectors in stage-paired timeout convergence diagnostics assertions:
  - replaced stage-paired tool/resource timeout convergence `expected_statuses=[ServerStatus.DEGRADED.value]` vectors with `list(SCRIPTED_FAILOVER_DEGRADED_EXPECTED_STATUSES)`.
  - kept diagnostics-filter and call-order assertions explicit at each test call site while reusing the shared degraded-status constant.
  - preserved invocation/connection filter semantics and call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated stage-paired timeout-stage failover expectation wiring in integration convergence assertions:
  - added shared helper `_stage_paired_failover_expectations_for_timeout_stage(...)` that maps `timeout_stage` to failover phase/server vectors and failover error-index constants.
  - migrated both stage-paired retry-window convergence tests (tool/resource) to consume the helper while keeping method-specific timeout-toggle wiring explicit at each test call site.
  - added focused regression coverage locking helper mapping semantics for both timeout stages and preserved call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated stage-paired failover invoke-timeout phase/server vectors in integration convergence assertions:
  - extracted shared constants `STAGE_PAIRED_INVOKE_TIMEOUT_FAILOVER_EXPECTED_PHASES` and `STAGE_PAIRED_INVOKE_TIMEOUT_FAILOVER_EXPECTED_SERVERS` for repeated invoke-timeout failover vector literals in tool/resource retry-window convergence checks.
  - migrated both stage-paired convergence invoke-timeout branches to consume the constants while keeping diagnostics-filter, timeout-category, and call-order assertions explicit.
  - added focused regression coverage locking invoke-timeout failover vector values and preserved call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated stage-paired failover initialize-timeout phase/server vectors in integration convergence assertions:
  - extracted shared constants `STAGE_PAIRED_INITIALIZE_TIMEOUT_FAILOVER_EXPECTED_PHASES` and `STAGE_PAIRED_INITIALIZE_TIMEOUT_FAILOVER_EXPECTED_SERVERS` for repeated initialize-timeout failover vector literals in tool/resource retry-window convergence checks.
  - migrated both stage-paired convergence initialize-timeout branches to consume the constants while keeping diagnostics-filter, timeout-category, and call-order assertions explicit.
  - added focused regression coverage locking initialize-timeout failover vector values and preserved call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated stage-paired failover initialize-stage error-index literals in integration convergence assertions:
  - extracted shared constant `STAGE_PAIRED_FAILOVER_INITIALIZE_ERROR_INDEX` for repeated `failover_error_index = 1` wiring in tool/resource retry-window convergence failover checks.
  - migrated both stage-paired convergence initialize-timeout branches to consume the constant while keeping diagnostics-filter, timeout-category, and call-order assertions explicit.
  - added focused regression coverage locking initialize-stage error-index constant value and preserved call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated stage-paired failover invoke-stage error-index literals in integration convergence assertions:
  - extracted shared constant `STAGE_PAIRED_FAILOVER_INVOKE_ERROR_INDEX` for repeated `failover_error_index = 3` wiring in tool/resource retry-window convergence failover checks.
  - migrated both stage-paired convergence branches to consume the constant while keeping diagnostics-filter, timeout-category, and call-order assertions explicit.
  - added focused regression coverage locking invoke-stage error-index constant value and preserved call-order literal/subsequence behavior unchanged.
- [x] Expanded scripted failover timeout-category constant adoption in integration invocation-event assertions:
  - migrated adjacent failover invocation-event assertions still using inline `"network_timeout"` literals to `SCRIPTED_FAILOVER_TIMEOUT_ERROR_CATEGORY`.
  - kept diagnostics-filter and call-order assertions explicit while reducing repeated timeout-category literal wiring in stage-paired tool/resource failover scenarios.
  - preserved invocation/connection filter semantics and call-order literal/subsequence parity behavior unchanged.
- [x] Reduced duplicated scripted mixed-method failover timeout-category assertions in integration diagnostics checks:
  - extracted shared constant `SCRIPTED_FAILOVER_TIMEOUT_ERROR_CATEGORY` for repeated scripted failover `"network_timeout"` invocation-event assertions.
  - migrated scripted mixed-method tool/resource failover invocation-event assertions to consume the shared timeout-category constant while keeping diagnostics-filter and call-order assertions explicit.
  - added focused regression coverage locking timeout-category constant value and preserved call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated scripted mixed-method failover degraded-status vectors in integration diagnostics assertions:
  - extracted shared tuple constant `SCRIPTED_FAILOVER_DEGRADED_EXPECTED_STATUSES` for repeated single-item degraded status expectations.
  - migrated scripted mixed-method tool/resource failover connection-event filter assertions to consume the shared constant while keeping diagnostics-filter call sites explicit.
  - added focused regression coverage locking degraded-status constant values and preserved call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated scripted mixed-method failover filter phase vectors in integration diagnostics assertions:
  - extracted shared tuple constant `SCRIPTED_FAILOVER_FILTER_EXPECTED_PHASES` for repeated 4-step failure filter phase expectations.
  - migrated scripted mixed-method tool/resource failover invocation-filter assertions to consume the shared constant while keeping diagnostics-filter call sites explicit.
  - added focused regression coverage locking filter-phase constant values and preserved call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated scripted mixed-method failover phase/server expectation vectors in integration call-order tests:
  - extracted shared tuple constants for the repeated 8-step failover invocation phase vector and method-specific server-order vectors.
  - migrated scripted mixed-method failover assertion wiring to use the shared constants while keeping diagnostics filter assertions explicit at test call sites.
  - added focused regression coverage locking failover constant values and preserved call-order literal/subsequence behavior unchanged.
- [x] Reduced duplicated mixed-method scripted request-id tuple wiring in integration call-order parity tests:
  - added shared helper `_mixed_method_scripted_request_ids(...)` and migrated scripted mixed-method parity assertion wiring to consume it.
  - added focused helper regression coverage to lock request-id tuple ordering semantics.
  - preserved diagnostics filter assertions, observed call-order literal assertions, and phase-start/transport subsequence parity behavior unchanged.
- [x] P01 `project_skeleton.md` baseline implemented: `pyproject.toml`, `src/` package layout, test directories, config/ui folders, and package entrypoint.
- [x] P03 `data_models.md` baseline implemented: `Project` + `ATTEvent` models, SQLite migrations, async store with CRUD and event queries.
- [x] P04-P11 baseline manager interfaces implemented in `src/att/core/` (`project_manager`, `code_manager`, `git_manager`, `runtime_manager`, `test_runner`, `debug_manager`, `deploy_manager`, `tool_orchestrator`).
- [x] Expanded `ProjectManager` with clone and archive-download operations (`clone`, `download`) including async git clone execution and archive creation.
- [x] P14 baseline API scaffolding implemented: FastAPI app, project/code/git/runtime/test/debug/deploy routes, health endpoint, WebSocket endpoint, and MCP discovery endpoint.
- [x] P02 CI workflows implemented: `.github/workflows/pr-quick.yml` and `.github/workflows/main-full.yml`.
- [x] P12 MCP server baseline expanded: full ATT tool/resource catalog + lookup helpers in `src/att/mcp/server.py`.
- [x] P13 MCP client baseline expanded: multi-server state model with health checks, exponential backoff, degraded/unreachable states, and transition audit events in `src/att/mcp/client.py`.
- [x] MCP API routes added for catalog and server management (`/api/v1/mcp/tools`, `/api/v1/mcp/resources`, `/api/v1/mcp/servers`, and health-check endpoints).
- [x] MCP unit test coverage added in `tests/unit/test_mcp_server.py` and `tests/unit/test_mcp_client.py`.
- [x] MCP invocation flow added with server failover: `tools/call` and `resources/read` JSON-RPC requests via `src/att/mcp/client.py`.
- [x] MCP invocation API endpoints added: `/api/v1/mcp/invoke/tool` and `/api/v1/mcp/invoke/resource` with 503 handling on all-server failure.
- [x] MCP management API expanded with server detail/delete and connection events endpoints (`/api/v1/mcp/servers/{name}`, `DELETE /api/v1/mcp/servers/{name}`, `/api/v1/mcp/events`).
- [x] MCP client/server handshake support added with persistent initialization metadata (`initialized`, `protocol_version`, `last_initialized_at`) and initialization APIs (`POST /api/v1/mcp/servers/{name}/initialize`, `POST /api/v1/mcp/servers/initialize`).
- [x] MCP invocation path now enforces per-server initialize handshake before `tools/call`/`resources/read` and automatically fails over when initialization fails.
- [x] Added combined MCP connect flow (health check + initialize) in client manager (`connect_server`, `connect_all`) and API (`POST /api/v1/mcp/servers/{name}/connect`, `POST /api/v1/mcp/servers/connect`).
- [x] Added explicit per-server MCP capability snapshots captured at initialize time and surfaced via MCP server APIs (`capability_snapshot` with protocol/server/capabilities metadata).
- [x] Added structured MCP invocation failure diagnostics (`method` + per-server initialize/invoke attempts) and deterministic 503 error detail payloads for invocation APIs.
- [x] Added MCP initialization freshness metadata (`initialization_expires_at`) and stale reinitialize gating before invocation, with mixed-state recovery sequencing coverage.
- [x] Added stable MCP transport error categorization (timeout/http-status/invalid-payload/rpc/transport) surfaced in server state (`last_error_category`) and invocation attempt diagnostics (`error_category`).
- [x] Added MCP invocation lifecycle event auditing with bounded retention and API exposure (`GET /api/v1/mcp/invocation-events`) for ordered initialize/invoke diagnostics.
- [x] Added cross-stream MCP diagnostics correlation/filtering: connection events now carry `correlation_id` linked to invocation `request_id`, and both event endpoints support deterministic server/method/request/correlation/limit query filters.
- [x] Added production-facing NAT MCP adapter path in `MCPClientManager` with adapter-first transport resolution, safe dependency wiring fallback, and adapter-focused parity/failover coverage.
- [x] Added adapter lifecycle controls and observability for MCP external sessions (`invalidate`/`refresh` + non-sensitive `adapter_session` diagnostics) with dedicated API endpoints and conflict handling when controls are unavailable.
- [x] Added deterministic adapter recovery semantics and operator capability visibility (`adapter_controls_available` on server/list payloads) with refresh-identity and transport-invalidation recreation coverage.
- [x] Added fleet-level adapter diagnostics aggregation endpoint (`GET /api/v1/mcp/adapter-sessions`) and multi-server partial-refresh failover/correlation resilience coverage.
- [x] Expanded adapter diagnostics aggregation controls with deterministic query filtering (`server`, `active_only`, `limit`) across manager and API surfaces.
- [x] Added mixed-state integration coverage validating invalidate-one-server isolation, including unaffected server session identity and capability-snapshot stability.
- [x] Added manager-sourced adapter session freshness semantics (`unknown`/`active_recent`/`stale`) surfaced in per-server and aggregated MCP diagnostics payloads.
- [x] Added mixed-state cluster coverage combining refresh + invalidate + timeout failover with deterministic correlation and server-local capability-snapshot retention/replacement assertions.
- [x] Expanded aggregated adapter diagnostics controls with `freshness` query filtering, preserving manager-sourced deterministic ordering and cross-surface freshness consistency.
- [x] Added retry-window convergence integration coverage across consecutive failover/recovery cycles, including timeout-stage-specific degraded/unreachable transitions with deterministic correlation streams.
- [x] Added `MCPClientManager` clock seam (`now_provider`) for deterministic retry-window and freshness-time progression in tests without direct retry-window state mutation.
- [x] Expanded clock-driven mixed-state MCP coverage by migrating remaining retry-window mutations to injected clock progression and adding capability-snapshot timing retention/replacement assertions under deterministic convergence flows.
- [x] Added shared MCP test-time clock support and stage-paired timeout convergence coverage (`initialize` vs `invoke`) with explicit stage-specific retry/status/snapshot timing assertions.
- [x] Extracted reusable MCP NAT test transport scaffolding into `tests/support/mcp_nat_helpers.py` (API fake session and cluster session factory/models) and migrated integration tests to shared helpers.
- [x] Extended stage-paired retry-window convergence coverage with deterministic diagnostics-filter assertions (`server`, `request_id`, `correlation_id`, `limit`) for both `/api/v1/mcp/events` and `/api/v1/mcp/invocation-events`.
- [x] Extracted unit MCP NAT session scaffolding into shared support (`FakeNatSession`, `FakeNatSessionFactory`) and migrated unit adapter/control coverage to shared helpers.
- [x] Extended diagnostics filter parity to `resources/read` failover/recovery paths with deterministic invocation (`server`, `method`, `request_id`, `limit`) and connection (`server`, `correlation_id`, `limit`) assertions.
- [x] Added stage-paired `resources/read` retry-window convergence coverage (`initialize` vs `invoke` timeout) with deterministic status/retry deltas, server-local capability snapshot timing assertions, and correlated diagnostics-filter checks.
- [x] Expanded shared cluster NAT helper controls for `resources/read` invoke failures/timeouts (`fail_on_resource_reads`, `fail_on_timeout_resource_reads`) and reused them in convergence coverage.
- [x] Extracted shared convergence assertion helpers into `tests/support/mcp_convergence_helpers.py` and migrated stage-paired tool/resource convergence tests to shared filter/phase assertions.
- [x] Added scripted per-server/per-method flapping controls (`set_failure_script`) to `ClusterNatSessionFactory` and mixed tool/resource scripted-flapping integration coverage for deterministic failover/correlation order.
- [x] Extended scripted-failure realism with initialize-stage script handling and precedence (scripted initialize actions now override set-based initialize timeout toggles when both are configured).
- [x] Migrated remaining diagnostics-filter integration assertions to shared convergence helpers for deterministic reuse across event/filter scenarios.
- [x] Added focused unit coverage for scripted NAT helper semantics across `initialize`, `tools/call`, and `resources/read` keys (ordering, unsupported actions, script exhaustion fallback to set-based toggles).
- [x] Added scripted `error` action convergence coverage for `initialize` and `invoke` failover paths with deterministic `transport_error` classification and correlation-filter assertions.
- [x] Extended scripted `error` convergence parity to `resources/read` for paired `initialize`/`invoke` failover paths, including deterministic invocation/connection filter assertions (`server`, `method`, `request_id`, `correlation_id`, `limit`).
- [x] Added helper-level failure-script isolation coverage for mixed `primary`/`backup` server + method scripts under shared `ClusterNatSessionFactory` state.
- [x] Extended scripted initialize-precedence parity to `resources/read`: integration coverage now proves scripted `initialize: ok` overrides set-based initialize timeout toggles, preserves deterministic filter behavior, and avoids degraded transition for the overridden request.
- [x] Added API-level mixed-script isolation regression coverage across sequential `tools/call` + `resources/read` requests, asserting only targeted server/method script queues are consumed while unrelated queues remain intact until exercised.
- [x] Added API-level mixed initialize+invoke script isolation coverage across `primary` and `backup`, asserting initialize-script queues are consumed independently from method-script queues while deterministic failover/correlation behavior is preserved.
- [x] Added API-level initialize-script exhaustion regression coverage proving fallback to set-based initialize timeout toggles after script depletion without mutating unrelated invoke method queues.
- [x] Added helper/API call-order parity coverage for mixed scripted failover:
  - unit coverage now asserts deterministic `ClusterNatSessionFactory.calls` ordering across mixed `initialize` + `tools/call` + `resources/read` scripted actions with paired `primary`/`backup` failover.
  - integration coverage now cross-checks `factory.calls` ordering against invocation-event `initialize_start`/`invoke_start` phase order for one mixed scripted `tools/call` + `resources/read` sequence while preserving existing diagnostics-filter assertions.
- [x] Added initialize-cache call-order parity coverage for repeated invocations:
  - unit coverage now validates repeated same-server invokes do not emit extra transport `initialize` calls until explicit adapter invalidation, with paired `tools/call` and `resources/read` checks.
  - unit coverage also asserts invalidation restores one transport `initialize` on next invoke and rotates to a new session id.
  - integration coverage now validates repeated same-server `tools/call` + `resources/read` requests without invalidation keep transport call order at one `initialize` followed by invoke calls, while invocation-event phase-start streams continue to match via subsequence parity and deterministic diagnostics filters.
- [x] Added force-reinitialize trigger call-order parity coverage:
  - unit coverage now validates stale-expiry and non-healthy-status trigger paths each force a transport `initialize` before the next invoke, with paired `tools/call` and `resources/read` assertions.
  - integration coverage now drives stale-expiry and degraded-status transitions between repeated same-server requests and verifies transport call-order includes the expected additional `initialize` calls.
  - integration coverage preserves deterministic diagnostics-filter assertions and maintains invocation-phase/transport-call subsequence parity checks across the trigger sequence.
- [x] Added retry-window gating call-order parity coverage:
  - unit coverage now validates both degraded and unreachable retry-window-closed servers are skipped without primary transport calls and deterministically re-enter with `initialize` before invoke once retry windows reopen.
  - unit coverage includes paired `tools/call` and `resources/read` assertions for method parity.
  - integration coverage now validates timeout -> closed retry window skip -> retry-window reopen sequencing while backup serves requests, including transport call-order subsequence parity with invocation phase starts and deterministic diagnostics-filter assertions per request.
- [x] Extended retry-window call-order parity to `resources/read` and backup-state matrix paths:
  - added helper-level `resources/read` matrix coverage distinguishing backup non-retryable degraded vs unreachable states under mixed preferred-server ordering, with deterministic primary re-entry ordering (`initialize` before `resources/read`).
  - added API-level `resources/read` retry-window regression mirroring timeout -> closed retry-window skip -> retry-window reopen sequencing while backup serves requests.
  - preserved deterministic diagnostics-filter assertions and invocation-phase/transport-call subsequence parity checks across all requests in the sequence.
- [x] Added unreachable-transition retry-window parity for `resources/read`:
  - added helper-level matrix coverage that drives primary `initialize` timeout transitions from degraded -> unreachable under healthy-first candidate ordering, including deterministic backup skip/re-entry behavior across both invoke methods.
  - added API-level `/api/v1/mcp/invoke/resource` unreachable-transition regression that forces a second primary initialize timeout, verifies closed-window skip while backup serves, and asserts primary re-entry call order (`initialize` then `resources/read`) with invocation-phase subsequence parity.
  - retained deterministic diagnostics-filter assertions (`server`, `method`, `request_id`, `correlation_id`, `limit`) including failed-request request-id recovery from invocation-event deltas.
- [x] Added unreachable-transition retry-window parity for `tools/call` and extracted failed-request helper reuse:
  - added API-level `/api/v1/mcp/invoke/tool` unreachable-transition regression mirroring healthy-first ordering constraints (primary initialize timeout -> backup serve -> forced second primary initialize timeout -> unreachable skip -> primary re-entry).
  - preserved deterministic diagnostics-filter assertions (`server`, `method`, `request_id`, `correlation_id`, `limit`) and invocation-phase/transport-call subsequence parity across the full request sequence.
  - extracted shared invocation-event delta helper for failed-request request-id recovery and applied it to both `tools/call` and `resources/read` unreachable-transition regressions to reduce brittle duplicated parsing.
- [x] Reduced unreachable-transition sequence duplication and expanded backup reinitialize parity:
  - extracted shared integration helper scaffolding for unreachable-transition request progression so `tools/call` and `resources/read` API regressions reuse the same first-failover/closed-window/forced-unreachable/skip/re-entry flow while keeping per-request diagnostics assertions explicit in each test.
  - added helper-level unit coverage asserting degraded backup reinitialize call-order parity (`initialize` before invoke) when primary is forced unreachable under mixed preferred ordering, with paired checks for both `tools/call` and `resources/read`.
  - preserved clock-driven semantics and transport-order assertions without direct retry-window state mutation.
- [x] Consolidated retry-window call-order subsequence helpers and extended non-retryable backup matrix:
  - added shared convergence helpers for collecting invocation events by request id, deriving phase-start call-order tuples, and asserting transport-call subsequence parity.
  - migrated retry-window gating and unreachable-transition API call-order tests (`tools/call` + `resources/read`) to the shared subsequence helpers to reduce repeated cursor-loop scaffolding.
  - added helper-level unit matrix coverage pairing primary unreachable with backup degraded/unreachable retry-window-closed states, asserting deterministic no-candidate failure and deterministic backup re-entry ordering (`initialize` before invoke) after retry-window reopen.
- [x] Completed remaining call-order helper migration and added simultaneous unreachable reopen ordering matrix:
  - migrated remaining integration call-order parity tests (`scripted call-order`, `repeated same-server initialize-cache`, `force-reinitialize trigger`) to shared subsequence helpers to remove repeated request-id event aggregation/cursor-loop scaffolding.
  - preserved explicit observed transport-call literals while asserting phase-start/transport subsequence parity through shared helper utilities.
  - added helper-level matrix coverage for simultaneous `UNREACHABLE` retry-window reopen with preferred-order determinism assertions via invocation `initialize_start` sequencing and successful transport-call ordering semantics.
- [x] Added API-level simultaneous `UNREACHABLE` retry-window reopen parity across tool/resource invoke paths:
  - added one parametrized integration regression covering both invoke endpoints and both preferred-order permutations under closed-window no-candidate and simultaneous reopen progression.
  - assertions now verify deterministic preferred-order candidate attempt sequencing via invocation `initialize_start` phases while preserving transport call-order semantics that only successful initialize/invoke calls are logged.
  - retained deterministic diagnostics filter parity (`server`, `method`, `request_id`, `correlation_id`, `limit`) and shared phase-start/transport subsequence checks for the reopen request.
- [x] Reduced duplicated retry-window API scenario scaffolding in integration tests:
  - added shared retry-window test harness setup helpers for cluster manager/session factory/clock/client creation and server registration.
  - added shared invoke-construction and progression helpers for retry-window gating and simultaneous unreachable-reopen sequences.
  - migrated tool/resource gating, tool/resource unreachable-transition, and simultaneous unreachable-reopen tests to shared progression scaffolding while preserving explicit per-request diagnostics assertions and explicit per-test transport call-order literals.
- [x] Reduced duplicated unreachable-transition primary diagnostics assertions:
  - added shared integration helper that asserts per-request primary invocation/connection diagnostics across unreachable-transition sequences based on method + request-id order.
  - migrated both tool and resource unreachable-transition parity tests to helper-driven diagnostics assertions while keeping explicit expected phase/status vectors visible at each call site.
  - preserved explicit per-test transport call-order literal assertions and existing phase-start/transport subsequence parity checks.
- [x] Reduced duplicated unreachable-transition call-order literal assertions:
  - added shared integration helper that asserts unreachable-transition `fifth_slice` and full `observed_call_order` literals per method using explicit expected tuple lists passed from each test.
  - migrated tool/resource unreachable-transition tests to helper-driven call-order literal assertions while keeping explicit expected tuple lists visible at call sites.
  - preserved existing diagnostics assertions and phase-start/transport subsequence parity checks.
- [x] Reduced duplicated retry-window gating call-order expectation vectors:
  - extracted shared module-level constants for method-specific retry-window gating call-order expectations (`expected_third_slice` and full `expected_observed_call_order` tuples).
  - migrated both tool/resource retry-window gating call-order tests to consume the shared constants via the shared call-order helper.
  - preserved helper invocation semantics, diagnostics-filter assertions, and phase-start/transport subsequence parity checks unchanged.
- [x] Reduced duplicated primary diagnostics helper wiring across retry-window and unreachable-transition paths:
  - consolidated duplicated primary request-id scoped invocation/connection diagnostics assertions into one shared integration helper.
  - migrated both tool/resource retry-window gating and tool/resource unreachable-transition call sites to the shared helper while keeping explicit expected phase/status vectors unchanged.
  - preserved existing call-order helper assertions and phase-start/transport subsequence parity checks unchanged.
- [x] Reduced duplicated unreachable-transition call-order expectation vectors:
  - extracted shared module-level constants for method-specific unreachable-transition call-order expectations (`expected_fifth_slice` and full `expected_observed_call_order` tuples).
  - migrated both tool/resource unreachable-transition call-order tests to consume these shared constants via the existing unreachable-transition call-order helper.
  - preserved helper invocation semantics, diagnostics-filter assertions, and phase-start/transport subsequence parity checks unchanged.
- [x] Reduced duplicated call-order collection scaffolding across retry-window and unreachable-transition call-order helpers:
  - added a shared method-scoped transport call-order collector for `initialize` + invoke tuple streams with optional starting offset support.
  - migrated both retry-window gating and unreachable-transition call-order helpers to consume the shared collector while preserving per-slice literal assertions.
  - preserved diagnostics-filter assertions and phase-start/transport subsequence parity checks unchanged.
- [x] Reduced duplicated request-id tuple scaffolding across retry-window and unreachable-transition integration assertions:
  - added shared helper utilities to derive ordered request-id tuples from retry-window and unreachable-transition sequence dataclasses.
  - migrated tool/resource retry-window gating and unreachable-transition tests to consume the shared request-id helpers for diagnostics/event filtering inputs.
  - preserved diagnostics-filter assertions, call-order literal assertions, and phase-start/transport subsequence parity checks unchanged.
- [x] Reduced duplicated expected-call-order derivation scaffolding across call-order parity integrations:
  - added shared helper utility that derives expected call-order tuples from request-id scoped invocation events.
  - migrated retry-window/unreachable-transition and adjacent mixed-method call-order tests to consume this helper instead of repeated event-collection + phase-start derivation scaffolding.
  - preserved request-id ordering semantics, call-order literal assertions, and phase-start/transport subsequence parity checks unchanged.
- [x] Reduced duplicated mixed-method observed-call-order collection scaffolding:
  - added shared helper utility to collect observed transport call-order tuples for mixed-method (`initialize` + `tools/call` + `resources/read`) scenarios.
  - migrated remaining mixed-method call-order tests to consume the helper while preserving explicit expected observed-order literals.
  - preserved diagnostics-filter assertions and phase-start/transport subsequence parity checks unchanged.
- [x] Normalized call-order expectation vector typing/signatures for consistency:
  - converted method-specific call-order expectation constants to immutable tuple-based vectors.
  - updated call-order helper signatures to accept `Sequence[tuple[str, str]]` and normalized assertions for sequence-backed expectation constants.
  - preserved call-order literal semantics, diagnostics-filter assertions, and phase-start/transport subsequence parity checks unchanged.
- [x] Normalized primary phase/status expectation vector typing for consistency:
  - converted primary unreachable-transition and retry-window gating phase/status expectation constants to immutable tuple-based inner vectors.
  - updated shared primary diagnostics helper typing to accept `Sequence[Sequence[str]]` and normalized assertion-boundary inputs to concrete lists.
  - preserved diagnostics-filter semantics, call-order literal assertions, and phase-start/transport subsequence parity checks unchanged.
- [x] Reduced duplicated call-order subsequence assertion wiring:
  - added shared helper that derives expected call-order from request ids and performs subsequence assertion against observed transport order.
  - migrated retry-window/unreachable-transition and adjacent call-order tests to the shared helper while preserving explicit observed-call-order literals.
  - preserved diagnostics-filter semantics and phase-start/transport subsequence behavior unchanged.
- [x] Reduced duplicated retry-window invoke-builder scaffolding:
  - added dedicated tool/resource invoke-builder wrapper helpers around shared preferred-server invoke construction.
  - migrated tool/resource retry-window gating and unreachable-transition tests to wrapper helpers, removing repeated inline invoke-path/payload scaffolding.
  - preserved request progression semantics, diagnostics assertions, and call-order parity checks unchanged.
- [x] Reduced duplicated retry-window unreachable-transition bootstrap wiring:
  - added a shared helper for method-specific unreachable-transition bootstrap (harness setup + primary initialize timeout script + invoke wiring + sequence run).
  - migrated tool/resource unreachable-transition retry-window tests to this helper while preserving explicit per-method diagnostics and call-order expectation constants.
  - preserved progression semantics, diagnostics-filter assertions, and phase-start/transport subsequence checks unchanged.
- [x] Reduced duplicated retry-window gating bootstrap wiring:
  - added a shared helper for method-specific retry-window gating bootstrap (harness setup + method-specific invoke failure script + invoke wiring + gating sequence run).
  - migrated tool/resource retry-window gating tests to this helper while preserving explicit per-method diagnostics/call-order vectors.
  - preserved progression semantics, diagnostics-filter assertions, and phase-start/transport subsequence checks unchanged.
- [x] Reduced duplicated primary success diagnostics assertion wiring in mixed-method call-order tests:
  - added shared helper for primary successful-request diagnostics (`initialize_success` + `invoke_success` phases) with per-request expected status handling.
  - migrated loop-based diagnostics assertions in repeated-same-server and force-reinitialize call-order tests to this helper.
  - preserved request sequencing, call-order literal assertions, and phase-start/transport subsequence checks unchanged.
- [x] Reduced duplicated mixed-method request-spec scaffolding in call-order tests:
  - extracted shared mixed-method primary request-spec constants used by repeated-same-server and force-reinitialize call-order tests.
  - extracted shared force-reinitialize expected-status vectors and rewired loop iteration to zip shared request specs with behavior-specific status expectations.
  - preserved reinitialize trigger mutations, diagnostics assertions, and call-order literal/subsequence checks unchanged.
- [x] Reduced duplicated mixed-method observed call-order literal vectors in call-order tests:
  - extracted shared expected observed call-order constants for repeated-same-server and force-reinitialize mixed-method call-order tests.
  - rewired both tests to assert against tuple-backed shared constants while preserving explicit expected-order vectors.
  - preserved diagnostics-filter assertions and phase-start/transport subsequence checks unchanged.
- [x] Reduced duplicated mixed-method call-order literal assertion wiring in call-order tests:
  - added shared helper to collect mixed-method observed transport call order and assert expected literal vectors.
  - migrated repeated-same-server and force-reinitialize call-order tests to helper-driven literal assertions while preserving explicit expected vectors at call sites.
  - preserved diagnostics-filter assertions and phase-start/transport subsequence checks unchanged.
- [x] Reduced duplicated mixed-method request-execution scaffolding in call-order tests:
  - added shared helper that executes mixed-method request sequences (request post + request-id collection + primary success diagnostics assertions).
  - added optional per-index pre-request mutation hook and migrated force-reinitialize trigger mutations to this hook while preserving explicit trigger conditions.
  - migrated repeated-same-server and force-reinitialize tests to helper-driven request execution while preserving explicit request-spec/status vectors and call-order expectations.
- [x] Reduced duplicated mixed-method primary setup scaffolding in call-order tests:
  - added shared helper for primary mixed-method harness setup (`ClusterNatSessionFactory` + `MCPClientManager` + `TestClient` + primary server registration).
  - helper supports optional `now_provider` injection and force-reinitialize coverage now consumes it to preserve deterministic stale-expiry trigger behavior.
  - migrated repeated-same-server and force-reinitialize tests to helper-driven setup while preserving explicit trigger mutations and call-order expectations.
- [x] Reduced duplicated mixed-method final parity assertion wiring in call-order tests:
  - added shared helper for mixed-method phase-start/transport subsequence parity assertions using request-id vectors and observed call-order tuples.
  - migrated repeated-same-server and force-reinitialize mixed-method call-order tests to helper-driven final parity assertions.
  - preserved explicit request-id sequencing, expected observed call-order literals, and diagnostics-filter semantics unchanged.
- [x] Expanded mixed-method parity-helper adoption scope in call-order tests:
  - migrated remaining scripted mixed-method call-order parity assertion call site to the shared mixed-method parity helper.
  - removed the last mixed-method direct invocation of `_assert_call_order_subsequence_for_requests(...)` at test call sites.
  - preserved request-id sequencing semantics, observed call-order collection behavior, and diagnostics-filter expectations unchanged.
- [x] Reduced duplicated retry-window gating call-order literal assertions:
  - added a shared integration helper that asserts retry-window gating backup-only skip slice behavior, primary re-entry `third_slice` literals, and full `observed_call_order` literals per method.
  - migrated both tool/resource retry-window gating tests to helper-driven call-order literal assertions while keeping explicit expected tuple literals visible at each call site.
  - preserved existing diagnostics-filter assertions and phase-start/transport subsequence parity checks unchanged.
- [x] Reduced duplicated retry-window gating expectation vectors:
  - extracted shared module-level constants for primary retry-window gating expected phase/status vectors.
  - added a shared integration helper to assert per-request primary invocation/connection diagnostics for retry-window gating sequences based on explicit method + request-id ordering.
  - migrated both tool/resource retry-window gating call-order tests to use the shared constants/helper while preserving explicit per-method transport call-order literals and phase-start/transport subsequence parity assertions.
- [x] Reduced duplicated unreachable-transition expectation vectors:
  - extracted shared module-level constants for primary unreachable-transition expected phase/status vectors.
  - migrated tool/resource unreachable-transition diagnostics assertions to consume shared vectors rather than repeated tuple literals.
  - preserved helper invocation semantics, call-order literal assertions, and phase-start/transport subsequence parity checks.
- [x] MCP integration coverage expanded for invocation and fallback behavior in `tests/integration/test_api_mcp.py`.
- [x] P11 orchestration baseline expanded: `ToolOrchestrator` now runs change+test(+optional commit) workflows with event persistence.
- [x] Added workflow and event APIs: `POST /api/v1/projects/{id}/workflows/change-test` and `GET /api/v1/projects/{id}/events`.
- [x] Added orchestration coverage in `tests/unit/test_tool_orchestrator.py` and `tests/integration/test_api_workflows_events.py`.
- [x] P16 self-bootstrap baseline added: `SelfBootstrapManager` coordinates branch/change/test/commit/push, optional CI polling, and optional health-check gating.
- [x] Added self-bootstrap API endpoint: `POST /api/v1/projects/{id}/self-bootstrap/run`.
- [x] Added self-bootstrap coverage in `tests/unit/test_self_bootstrap_manager.py` and `tests/integration/test_api_self_bootstrap.py`.
- [x] Expanded self-bootstrap with PR lifecycle hooks (create + optional auto-merge) and rollback-on-unhealthy deploy behavior.
- [x] Replaced Git API placeholders with manager-backed Actions/PR operations in `src/att/api/routes/git.py` and `src/att/core/git_manager.py`.
- [x] Added self-bootstrap watchdog-style health retry controls before rollback (`health_check_retries`, `health_check_interval_seconds`).
- [x] Wired baseline live self-bootstrap adapters in API deps (CI status from `gh run list`, PR create/merge hooks via `gh` CLI).
- [x] Added CI status parser helper and unit coverage in `src/att/core/self_bootstrap_integrations.py` and `tests/unit/test_self_bootstrap_integrations.py`.
- [x] Expanded self-bootstrap with restart-watchdog polling controls (`restart_watchdog_retries`, `restart_watchdog_interval_seconds`) and rollback on unstable post-deploy runtime.
- [x] Wired baseline deploy/restart/rollback adapters into self-bootstrap deps (`DeployManager.run`, `RuntimeManager.status`, `RuntimeManager.stop`) and surfaced `restart_watchdog_status` in API responses.
- [x] Expanded MCP transport endpoint at `POST /mcp` with MCP handshake methods (`initialize`, `notifications/initialized`, `ping`) and manager-backed ATT tool/resource handlers aligned to the registered catalog.
- [x] Added MCP transport integration coverage in `tests/integration/test_mcp_transport.py` for handshake, tool invocation, resource reads, and error cases.
- [x] Implemented typed MCP project-tool adapter parsing in `src/att/mcp/tools/project_tools.py` and wired transport project operations to this adapter for normalized argument validation/execution.
- [x] Implemented typed MCP code-tool adapter parsing in `src/att/mcp/tools/code_tools.py` and wired transport code operations to this adapter for normalized argument validation/execution.
- [x] Implemented typed MCP git-tool adapter parsing in `src/att/mcp/tools/git_tools.py` and wired transport git operations to this adapter for normalized argument validation/execution.
- [x] Implemented typed MCP runtime/test tool adapter parsing in `src/att/mcp/tools/runtime_tools.py` and `src/att/mcp/tools/test_tools.py`, wired transport runtime/test operations to these adapters for normalized argument validation/execution.
- [x] Implemented typed MCP debug/deploy tool adapter parsing in `src/att/mcp/tools/debug_tools.py` and `src/att/mcp/tools/deploy_tools.py`, wired transport debug/deploy operations to these adapters for normalized argument validation/execution.
- [x] Implemented typed MCP resource URI parsing in `src/att/mcp/tools/resource_refs.py` and wired `resources/read` flow to this adapter for normalized resource dispatch.
- [x] Added project clone/download API coverage in `tests/integration/test_api_projects.py` and unit coverage for clone/download logic in `tests/unit/test_project_manager.py`.
- [x] Implemented `att.project.download` in MCP transport and added defensive JSON-RPC error wrapping for unexpected tool/resource handler exceptions.
- [x] Replaced e2e placeholder with real API smoke tests in `tests/e2e/test_placeholder.py` (health endpoint, MCP discovery, and MCP tools surface check).
- [x] Test scaffolding added under `tests/unit`, `tests/integration`, `tests/property`, and `tests/e2e` for the implemented baseline.
- [x] API coverage hardening pass completed for current endpoints (`code`, `git`, `runtime`, `test`, `debug`, `deploy`) with integration tests in `tests/integration/test_api_feature_endpoints.py`.
- [x] Runtime process output capture implemented in `RuntimeManager` via a bounded in-memory log buffer drained from subprocess stdout/stderr.
- [x] Runtime log reads are now manager-backed across API and MCP surfaces (`GET /api/v1/projects/{id}/runtime/logs`, `att.runtime.logs`, and `att://project/{id}/logs`).
- [x] Added runtime log coverage in `tests/unit/test_runtime_manager.py` and expanded MCP transport integration assertions in `tests/integration/test_mcp_transport.py`.
- [x] Expanded `TestRunner` execution output with parsed pytest summary metrics (pass/fail/skip/error counts, duration, no-tests flag) and timeout handling.
- [x] Added pytest summary parsers for console, JSON report, and JUnit XML inputs in `src/att/core/test_runner.py`.
- [x] Wired enriched test-run payloads through API and MCP transport (`/api/v1/projects/{id}/test/run`, `att.test.run`, `att.test.results`) including optional marker and timeout inputs.
- [x] Added test-runner unit coverage in `tests/unit/test_test_runner.py` and expanded test-tool adapter coverage in `tests/unit/test_test_tools.py`.
- [x] Added `RuntimeManager.probe_health()` with typed `RuntimeHealthProbe` output and optional configured process+HTTP+command probes.
- [x] Runtime status surfaces now emit health diagnostics (`healthy`, `health_probe`, `health_reason`, `health_checked_at`) via API (`GET /api/v1/projects/{id}/runtime/status`) and MCP (`att.runtime.status`).
- [x] Self-bootstrap restart watchdog now consumes runtime probe signals and surfaces restart diagnostics (`restart_watchdog_reason`) through manager results + API response payloads.
- [x] Added cursor-based runtime log streaming reads in manager/API/MCP (`RuntimeManager.read_logs`, `GET /api/v1/projects/{id}/runtime/logs`, `att.runtime.logs`, and `att://project/{id}/logs?cursor=...&limit=...`).
- [x] Added baseline release-aware rollback metadata in self-bootstrap (`requested_release_id`, `previous_release_id`, `rollback_release_id`) and surfaced resolved rollback target diagnostics in manager/API results.
- [x] Integrated release metadata source resolution for self-bootstrap rollback defaults via git (`HEAD`/`HEAD^`) and surfaced `release_metadata_source` in API responses.
- [x] Added rollback policy gating/validation outcomes in self-bootstrap (`rollback_policy_status`, `rollback_policy_reason`, `rollback_target_valid`) with deny-before-execute behavior for invalid targets.
- [x] Added self-bootstrap release-source adapter abstraction (`ReleaseSourceContext`, `ReleaseSourceAdapter`) with fallback-chain resolution and backward-compatible legacy provider support.
- [x] Expanded self-bootstrap rollback policy matrix with failure-class/deployment-context controls (`rollback_on_*_failure`, `deployment_context`) and result diagnostics (`rollback_failure_class`, `rollback_deployment_context`).
- [x] Wired runtime-log release metadata adapter + git fallback in API deps for release source-of-truth resolution beyond commit history only.
- [x] Fixed `code` route precedence bug: static `files/search` and `files/diff` routes now resolve before `files/{file_path:path}`.
- [x] Added project-existence validation for feature endpoints where `project_id` is in the path.
- [x] Local development environment bootstrapped in `.venv313` with project + dev dependencies installed.
- [x] Validation on 2026-02-13: `ruff format`, `ruff check`, `mypy`, and `pytest` all passing (235 tests).
- [x] Sub-plan files scaffolded in `todo/plans/` (`P01` through `P25`) for ongoing detailed planning and tracking.
- [ ] P12/P13 still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- [ ] P16 is in progress (restart watchdog/runtime health/log streaming + release-aware rollback metadata/policy gates + release-source adapter fallback + failure-class/deployment-context policy matrix are implemented; remaining work is deeper production rollout hardening).
- [ ] P15 and P17-P25 not started (planned phases remain unchanged).
- [ ] Remaining work is focused on replacing stubs with full implementations and completing Phase 1 self-bootstrapping.

## Reference Technologies

- [NVIDIA NeMo Agent Toolkit](https://developer.nvidia.com/nemo-agent-toolkit) — core framework (FastAPI frontend, YAML-driven workflows, MCP/A2A support)
- [NeMo Agent Toolkit UI](https://github.com/NVIDIA/NeMo-Agent-Toolkit-UI) — Next.js reference UI (proxy architecture, WebSocket, HITL workflows)
- [MCP UI](https://mcpui.dev/) — sandboxed iframe UI rendering for MCP tools, multi-SDK
- [OpenAI Apps SDK](https://developers.openai.com/apps-sdk/) — MCP-server-based apps with native UI, discovery, deployment pipeline
- [MCP Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25) — JSON-RPC protocol, tools/resources/prompts/roots, Streamable HTTP transport

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ATT Web UI                           │
│   (NAT FastAPI Frontend + NAT-UI + Ace Editor)          │
│   Project Manager │ Code Editor │ Terminal │ Logs │ Chat│
├────────────────────────┬────────────────────────────────┤
│   ATT API Server       │     MCP Server (Streamable HTTP)│
│   (FastAPI/OpenAPI)    │     Tools: project, code, git,  │
│   REST + WebSocket     │     deploy, debug, test, runtime │
├────────────────────────┴────────────────────────────────┤
│                ATT Core Engine                          │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐│
│   │ Project  │ │ Code     │ │ Git/CI   │ │ Runtime   ││
│   │ Manager  │ │ Manager  │ │ Manager  │ │ Manager   ││
│   └──────────┘ └──────────┘ └──────────┘ └───────────┘│
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐│
│   │ Test     │ │ Debug    │ │ Deploy   │ │ Tool      ││
│   │ Runner   │ │ Manager  │ │ Manager  │ │ Orchestr. ││
│   └──────────┘ └──────────┘ └──────────┘ └───────────┘│
├─────────────────────────────────────────────────────────┤
│                  MCP Client Layer                       │
│   Connects to: Claude Code, Codex, Windsurf, GitHub,   │
│   filesystem, terminal, NAT profiler, other MCP servers │
│   (multi-server from Phase 1 — availability failover)   │
├─────────────────────────────────────────────────────────┤
│                  NAT Runtime                            │
│   nat serve │ YAML configs │ workflow engine │ profiler │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, NAT (`nvidia-nat`) |
| Frontend | NAT FastAPI Frontend + NAT-UI (Next.js/React/TypeScript) + Ace Editor |
| Protocol | MCP via NAT built-in (`nat.mcp`), OpenAPI 3.1 |
| Database | SQLite (local), PostgreSQL (cloud) |
| Queue | Redis (optional, for async jobs) |
| Package Manager | `uv` (Astral) |
| NAT Version | 1.4.x (`nvidia-nat[mcp]`) |
| Testing | pytest, hypothesis, playwright, mypy, ruff |
| CI/CD | GitHub Actions (tiered) |
| Containers | Docker / Docker Compose (optional — not required) |
| Deployment | Local-first (direct subprocess via `nat serve`), cloud migration path later |
| Process Model | Single managed NAT app at a time, subprocess isolation (ATT itself always runs) |

---

## Phase Plan

### Phase 0: Foundation (self-bootstrapping prerequisite)
**Goal**: Skeleton project with CI, core managers, and basic web UI.

### Phase 1: Self-Bootstrapping MVP
**Goal**: ATT can edit its own code, run its own tests, create PRs, and merge changes.

### Phase 2: Full NAT App Development
**Goal**: Users can create, run, debug, and deploy arbitrary NAT apps through the web UI.

### Phase 3: Cloud & Production Hardening
**Goal**: Cloud deployment, multi-user, security, observability.

---

## Phase 0: Foundation

### 0.1 Project Skeleton
- Initialize Python project with `uv` and `pyproject.toml`
- Directory structure:

```
att/
├── src/
│   └── att/
│       ├── __init__.py
│       ├── core/                  # Core engine modules
│       │   ├── __init__.py
│       │   ├── project_manager.py
│       │   ├── code_manager.py
│       │   ├── git_manager.py
│       │   ├── runtime_manager.py
│       │   ├── test_runner.py
│       │   ├── debug_manager.py
│       │   ├── deploy_manager.py
│       │   └── tool_orchestrator.py
│       ├── api/                   # FastAPI routes + OpenAPI
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── routes/
│       │   └── schemas/
│       ├── mcp/                   # MCP server + client (thin wrappers around nat.mcp)
│       │   ├── __init__.py
│       │   ├── server.py          # Registers ATT tools with nat.mcp server
│       │   ├── client.py          # Multi-server connection manager using nat.mcp client
│       │   └── tools/             # ATT tool definitions exposed via MCP
│       ├── nat_integration/       # NAT workflow configs + plugins
│       │   ├── __init__.py
│       │   ├── configs/
│       │   └── workflows/
│       ├── models/                # Data models
│       │   ├── __init__.py
│       │   ├── project.py
│       │   └── events.py
│       └── db/                    # SQLite persistence layer
│           ├── __init__.py
│           ├── store.py           # SQLite connection + queries
│           └── migrations.py      # Schema versioning
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   └── e2e/
├── configs/                       # NAT YAML configs for ATT itself
├── ui/                            # ATT-specific UI extensions for NAT-UI (no fork)
├── .github/
│   └── workflows/
│       ├── pr-quick.yml           # Tier 1: fast PR checks
│       └── main-full.yml          # Tier 2: full pre-merge
├── pyproject.toml
├── Dockerfile                     # Optional — not required for local dev
├── docker-compose.yml             # Optional — not required for local dev
└── README.md
```

- Dependencies: `nvidia-nat[mcp]` (1.4.x — includes fastapi, uvicorn, pydantic), `httpx`, `aiosqlite`
- Dev dependencies: `pytest`, `pytest-asyncio`, `hypothesis`, `playwright`, `mypy`, `ruff`, `coverage`, `pytest-cov`

### 0.2 CI/CD — Tiered GitHub Actions

**Tier 1: PR Quick Checks** (`pr-quick.yml` — runs on PR to `dev`)
- Trigger: `pull_request` targeting `dev`
- Steps:
  1. Lint with `ruff check` and `ruff format --check` (~5s)
  2. Type check with `mypy --strict` (~10s)
  3. Unit tests with `pytest tests/unit/ -x --timeout=30` (~15s)
  4. Property tests with `pytest tests/property/ -x --timeout=60` (~30s)
  5. Coverage gate: fail if < 80%
- Target: < 2 minutes total

**Tier 2: Full Pre-Merge** (`main-full.yml` — runs on PR to `main`)
- Trigger: `pull_request` targeting `main`
- Steps:
  1. Everything from Tier 1
  2. Integration tests: `pytest tests/integration/ --timeout=120` (~2min)
  3. E2E tests: `pytest tests/e2e/ --timeout=300` (~5min)
  4. Security scan: `bandit -r src/`
  5. Dependency audit: `pip-audit`
  6. Smoke test: start server (subprocess), hit health endpoint, shut down
  7. (Optional, if Docker available) Build Docker image and smoke test it
- Target: < 10 minutes total

### 0.3 Core Data Models

```python
# project.py
class Project(BaseModel):
    id: str
    name: str
    path: Path
    git_remote: str | None
    nat_config_path: Path | None  # None until project has a NAT config
    status: ProjectStatus  # created | cloned | running | stopped | error
    created_at: datetime
    updated_at: datetime

class ProjectStatus(str, Enum):
    CREATED = "created"
    CLONED = "cloned"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

# events.py
class ATTEvent(BaseModel):
    id: str
    project_id: str
    event_type: EventType
    payload: dict
    timestamp: datetime

class EventType(str, Enum):
    PROJECT_CREATED = "project.created"
    CODE_CHANGED = "code.changed"
    TEST_RUN = "test.run"
    TEST_PASSED = "test.passed"
    TEST_FAILED = "test.failed"
    BUILD_STARTED = "build.started"
    BUILD_COMPLETED = "build.completed"
    DEPLOY_STARTED = "deploy.started"
    DEPLOY_COMPLETED = "deploy.completed"
    GIT_COMMIT = "git.commit"
    GIT_PR_CREATED = "git.pr.created"
    GIT_PR_MERGED = "git.pr.merged"
    ERROR = "error"
```

**Persistence:** Both `Project` and `ATTEvent` are stored in SQLite via `db/store.py`.
Events are append-only (audit log) and retained until manual cleanup. The store
provides async query methods for filtering events by project, type, and time range.

### 0.4 Core Managers (interfaces first, TDD)

Each manager is developed interface-first with tests written before implementation.

**ProjectManager** — create, list, clone, download, delete projects
**CodeManager** — read, write, search, diff files within a project
**GitManager** — status, add, commit, push, branch, PR, merge, log, diff
**RuntimeManager** — start (`nat serve`), stop, restart, status, logs (single app at a time, subprocess)
**TestRunner** — run unit/integration/e2e tests, parse results, report; use TDD and ensure tests pass
**DebugManager** — read logs, read errors, fetch stack traces, attach profiler
**DeployManager** — build, deploy (local subprocess primary, Docker optional)
**ToolOrchestrator** — coordinate multi-step workflows across managers

---

## Phase 1: Self-Bootstrapping MVP

### 1.1 MCP Server — Expose ATT Tools
Expose each manager operation as an MCP tool via Streamable HTTP transport:

| Tool Name | Description |
|-----------|-------------|
| `att.project.create` | Create a new NAT project from template or clone from URL |
| `att.project.download` | Download a pre-built project artifact/zip |
| `att.project.list` | List all projects |
| `att.project.status` | Get project status |
| `att.project.delete` | Delete a project |
| `att.code.list` | List file tree for project |
| `att.code.read` | Read file contents |
| `att.code.write` | Write/update file contents |
| `att.code.search` | Search across project files |
| `att.code.diff` | Show diff of changes |
| `att.git.status` | Git status of project |
| `att.git.commit` | Stage and commit changes |
| `att.git.push` | Push to remote |
| `att.git.branch` | Create/switch branches |
| `att.git.pr.create` | Create pull request |
| `att.git.pr.merge` | Merge pull request |
| `att.git.pr.review` | Get PR review comments |
| `att.git.log` | Git log |
| `att.git.actions` | Get GitHub Actions status/logs |
| `att.runtime.start` | Start NAT workflow server |
| `att.runtime.stop` | Stop NAT workflow server |
| `att.runtime.logs` | Get runtime logs |
| `att.runtime.status` | Get runtime status |
| `att.test.run` | Run test suite (unit/integration/e2e) |
| `att.test.results` | Get test results |
| `att.debug.errors` | Get current errors/stack traces |
| `att.debug.logs` | Get filtered debug logs |
| `att.deploy.build` | Build deployment artifact (subprocess or Docker) |
| `att.deploy.run` | Deploy to target (subprocess restart, or Docker run if available) |
| `att.deploy.status` | Get current deployment status |

MCP Resources:
| Resource URI | Description |
|-------------|-------------|
| `att://projects` | List of all projects |
| `att://project/{id}/files` | File tree for project |
| `att://project/{id}/config` | NAT YAML config |
| `att://project/{id}/tests` | Latest test results |
| `att://project/{id}/logs` | Runtime logs |
| `att://project/{id}/ci` | CI pipeline status |

### 1.2 MCP Client — Connect to External Tools
Connect to multiple external MCP servers from Phase 1. Multi-server support is a high priority because different servers have different capabilities and availability levels. ATT must handle servers being down or unreachable gracefully — retry with backoff, fall back to alternatives, and continue operating in degraded mode.

| External Server | Purpose | Phase |
|----------------|---------|-------|
| Claude Code MCP | AI-assisted code editing, review, explanation | 1 |
| GitHub MCP | Issues, PRs, actions, code search | 1 |
| Filesystem MCP | Direct file access | 1 |
| Terminal MCP | Shell command execution | 1 |
| Windsurf | AI code assistant (alternative to Claude Code) | 1 |
| Codex | AI code assistant (alternative to Claude Code) | 1 |

**Availability handling:**
- Health check each connected server periodically
- On connection failure: retry with exponential backoff (1s, 2s, 4s, 8s)
- If a server is unreachable, mark as degraded and continue with remaining servers
- Log all connection state changes
- UI shows server health status

The MCP client uses NAT's built-in MCP integration (`nat.mcp`) with dynamic server discovery and configuration stored per-project.

### 1.3 OpenAPI Interface
All REST endpoints auto-generate OpenAPI 3.1 spec via FastAPI:

```
# Projects
GET    /api/v1/projects                          # List all projects
POST   /api/v1/projects                          # Create from template or clone from URL
POST   /api/v1/projects/download                  # Download pre-built artifact/zip
GET    /api/v1/projects/{id}                      # Get project details + status
DELETE /api/v1/projects/{id}                      # Delete project

# Code
GET    /api/v1/projects/{id}/files                # File tree listing
GET    /api/v1/projects/{id}/files/{path}         # Read file contents
PUT    /api/v1/projects/{id}/files/{path}         # Write/update file
POST   /api/v1/projects/{id}/files/search         # Search across files
GET    /api/v1/projects/{id}/files/diff            # Show current diff

# Git
GET    /api/v1/projects/{id}/git/status           # Git status
POST   /api/v1/projects/{id}/git/commit           # Stage + commit
POST   /api/v1/projects/{id}/git/push             # Push to remote
POST   /api/v1/projects/{id}/git/branch           # Create/switch branch
GET    /api/v1/projects/{id}/git/log              # Commit log
GET    /api/v1/projects/{id}/git/actions           # GitHub Actions status/logs
POST   /api/v1/projects/{id}/git/pr               # Create pull request
POST   /api/v1/projects/{id}/git/pr/merge         # Merge pull request
GET    /api/v1/projects/{id}/git/pr/reviews        # Get PR review comments

# Runtime
POST   /api/v1/projects/{id}/runtime/start        # Start nat serve
POST   /api/v1/projects/{id}/runtime/stop         # Stop nat serve
GET    /api/v1/projects/{id}/runtime/status        # Running/stopped/health
GET    /api/v1/projects/{id}/runtime/logs          # Runtime logs (with streaming via Accept header)

# Test
POST   /api/v1/projects/{id}/test/run             # Run test suite
GET    /api/v1/projects/{id}/test/results          # Get test results + coverage

# Debug
GET    /api/v1/projects/{id}/debug/errors          # Current errors/stack traces
GET    /api/v1/projects/{id}/debug/logs            # Filtered debug logs

# Deploy
POST   /api/v1/projects/{id}/deploy/build         # Build artifact
POST   /api/v1/projects/{id}/deploy/run           # Deploy (subprocess or Docker)
GET    /api/v1/projects/{id}/deploy/status         # Deployment status

# Streaming & System
WS     /api/v1/projects/{id}/ws                    # WebSocket for event streaming
GET    /api/v1/health                              # Server health check
GET    /api/v1/mcp/.well-known                     # MCP server discovery
```

### 1.4 Web UI — NAT Frontend Integration
Build on the NAT FastAPI Frontend + NAT-UI:

**Views:**
1. **Dashboard** — project list, status overview, quick actions
2. **Project View** — file tree, code editor (Ace), terminal, logs
3. **Git View** — branch visualization, diff viewer, PR management
4. **Test View** — test results, coverage reports, failure details
5. **Runtime View** — server status, log streaming, health metrics
6. **Deploy View** — build status, deployment targets, deployment history
7. **Chat View** — NAT-style chat with ATT agent for natural language interaction
8. **Settings** — MCP server connections, tool configuration, project templates

### 1.5 Self-Bootstrap Capability
The critical milestone — ATT operating on its own codebase. **Fully autonomous** by default: ATT can complete the entire cycle without human intervention when CI is green. It *can* request human review/approval when it chooses to (e.g., for high-risk changes), but is not required to.

1. ATT registers itself as a project (pointing to its own repo)
2. User (or AI agent via MCP/chat) requests a change
3. ATT creates a branch via GitManager
4. ATT edits its own source via CodeManager
5. ATT runs its own tests via TestRunner (local, fast feedback)
6. ATT creates a PR via GitManager
7. CI runs (GitHub Actions Tier 1) — ATT polls for results
8. On CI pass, ATT merges the PR autonomously
9. ATT triggers a graceful self-restart via DeployManager:
   a. ATT spawns a new process from the updated code
   b. New process starts and begins accepting requests
   c. Old process drains in-flight requests and exits
   d. (Implementation: use `exec` to replace process, or a lightweight
      watchdog/launcher script that restarts ATT when it exits with a
      "restart requested" exit code)
10. Health check confirms new version is running

**Safety rails:**
- All tests must pass before merge (local + CI)
- Health check after deploy; auto-rollback on failure
- ATT may optionally request human review for changes it deems high-risk
- Full audit log of every autonomous action

**Self-bootstrap branching strategy:**
- ATT creates feature branches off `dev`
- PRs target `dev` (triggers Tier 1 quick checks)
- After merge to `dev`, a separate PR from `dev` → `main` triggers Tier 2 full checks
- For urgent self-fixes, ATT can PR directly to `main` (triggers both tiers)

**CI polling:**
- ATT polls GitHub Actions API for workflow run status
- Poll interval: 10s with exponential backoff to 60s
- Timeout: configurable (default 10 minutes)
- Handle GitHub API being unreachable (retry with backoff)

**Health check after self-restart:**
- The watchdog/launcher script (not ATT itself) performs the health check
- Watchdog starts new ATT process, polls `GET /api/v1/health` with timeout
- On health check pass: watchdog exits successfully (new ATT takes over)
- On health check fail: watchdog kills new process, restarts old version, emits error event

---

## Phase 2: Full NAT App Development

### 2.1 Project Templates
- Starter templates for common NAT app patterns (chatbot, RAG, multi-agent, tool-server)
- Template registry with versioning
- `nat init`-style project scaffolding through the UI

### 2.2 NAT Config Editor
- Visual YAML config editor with validation
- Component browser (LLMs, tools, workflows)
- Live preview of workflow graph

### 2.3 Tool Marketplace / MCP Registry
- Browse and connect to MCP servers from registry
- Publish ATT-created tools as MCP servers
- A2A agent discovery and connection

### 2.4 Advanced Debugging
- NAT profiler integration (token usage, latency, cost)
- Execution trace visualization
- Breakpoint-style step-through for agent workflows
- Live log filtering and search

### 2.5 Deployment Pipelines
- One-click deploy to Docker/K8s
- Environment management (dev/staging/prod)
- Rollback support
- Blue/green deployments

---

## Phase 3: Cloud & Production Hardening

### 3.1 Multi-User Support
- Authentication (OAuth 2.0 / API keys)
- Per-user project isolation
- Role-based access control

### 3.2 Cloud Deployment
- PostgreSQL for persistent storage
- Redis for job queues and caching
- Kubernetes manifests / Helm charts
- Cloud provider integrations (AWS, GCP, Azure)

### 3.3 Observability
- OpenTelemetry integration
- Structured logging (JSON)
- Metrics dashboard
- Alerting rules

### 3.4 Security
- Input sanitization on all endpoints
- Sandboxed code execution for managed projects
- Secret management (no plaintext secrets in configs)
- Dependency vulnerability scanning
- Rate limiting

---

## Detailed Sub-Plans Required

Each sub-plan will be a separate document in `todo/plans/` with full specifications, tests, and acceptance criteria.

| # | Sub-Plan | Dependencies | Phase |
|---|----------|-------------|-------|
| P01 | `project_skeleton.md` — uv setup, pyproject.toml, directory structure, dev tooling | None | 0.1 |
| P02 | `ci_github_actions.md` — Tier 1 + Tier 2 workflow definitions, matrix strategy | P01 | 0.2 |
| P03 | `data_models.md` — Pydantic models, SQLite store, schema migrations, event audit log | P01 | 0.3 |
| P04 | `project_manager.md` — CRUD, template instantiation, project lifecycle | P03 | 0.4 |
| P05 | `code_manager.md` — file read/write/search/diff, working directory isolation | P03 | 0.4 |
| P06 | `git_manager.md` — all git operations, GitHub API integration | P03 | 0.4 |
| P07 | `runtime_manager.md` — nat serve lifecycle, log capture, health checks | P03, P04 | 0.4 |
| P08 | `test_runner.md` — test execution, result parsing, coverage reporting | P03, P05 | 0.4 |
| P09 | `debug_manager.md` — error collection, log filtering, profiler integration | P03, P07 | 0.4 |
| P10 | `deploy_manager.md` — subprocess deploy, optional Docker, health verification, rollback | P03, P07 | 0.4 |
| P11 | `tool_orchestrator.md` — multi-step workflow coordination, event bus | P04-P08, P10 | 0.4 |
| P12 | `mcp_server.md` — tool registration via `nat.mcp`, Streamable HTTP transport | P04-P08, P10 | 1.1 |
| P13 | `mcp_client.md` — multi-server from Phase 1, discovery, health checks, failover, tool invocation | P11 | 1.2 |
| P14 | `openapi_routes.md` — REST endpoints, request validation, error handling | P04-P08, P10 | 1.3 |
| P15 | `web_ui.md` — NAT-UI integration (no fork), Ace editor, views, WebSocket streaming | P14 | 1.4 |
| P16 | `self_bootstrap.md` — fully autonomous self-modification, CI polling, safety rails, rollback | P04-P13 | 1.5 |
| P17 | `project_templates.md` — template system, registry, scaffolding | P04 | 2.1 |
| P18 | `nat_config_editor.md` — visual YAML editor, component browser | P15 | 2.2 |
| P19 | `mcp_registry.md` — marketplace, discovery, publishing | P12, P13 | 2.3 |
| P20 | `advanced_debugging.md` — profiler UI, execution traces, breakpoints | P09, P15 | 2.4 |
| P21 | `deploy_pipelines.md` — multi-env, rollback, blue/green | P10, P15 | 2.5 |
| P22 | `multi_user.md` — auth, isolation, RBAC | P14 | 3.1 |
| P23 | `cloud_deploy.md` — PostgreSQL, Redis, K8s, Helm | P10, P22 | 3.2 |
| P24 | `observability.md` — OpenTelemetry, metrics, alerting | P14 | 3.3 |
| P25 | `security_hardening.md` — sandboxing, secrets, scanning, rate limiting | P14, P22 | 3.4 |

### Dependency Graph (Critical Path to Self-Bootstrapping)

```
P01 → P02
P01 → P03 → P04 → P07 → P10 ──┐
              ├──→ P05 → P08 ──┤
              ├──→ P06 ────────┤
              └──→ P09 (not on critical path for self-bootstrap)
                               │
{P04,P05,P06,P08,P10} → P11 → P12 ──→ P16 (self-bootstrap)
                         P11 → P13 ──→ P16
          {P04-P08, P10} → P14 → P15 → P16
```

**Shortest path to self-bootstrap**: P01 → P03 → {P04, P05, P06, P08, P10} → P11 → {P12, P13, P14} → P16

Note: P04, P05, P06, P08, P10 can be parallelized. P09 (DebugManager) is not on
the critical path for self-bootstrap but is needed for Phase 2.

---

## Full Test List

Tests are organized by level and module. Each test name encodes what it verifies. Tests marked with `[EDGE]` cover edge cases. Tests marked with `[SELF]` are specifically for the self-bootstrapping workflow.

### Unit Tests

#### Project Manager (`tests/unit/test_project_manager.py`)
```
test_create_project_returns_project_with_status_created
test_create_project_generates_unique_id
test_create_project_creates_directory_structure
test_create_project_from_template_copies_files
test_create_project_with_duplicate_name_raises_error [EDGE]
test_create_project_with_invalid_name_raises_validation_error [EDGE]
test_create_project_with_empty_name_raises_validation_error [EDGE]
test_create_project_name_with_special_characters_sanitized [EDGE]
test_list_projects_returns_all_projects
test_list_projects_empty_returns_empty_list
test_get_project_by_id_returns_correct_project
test_get_project_by_nonexistent_id_raises_not_found [EDGE]
test_delete_project_removes_directory
test_delete_project_nonexistent_raises_not_found [EDGE]
test_delete_running_project_stops_first [EDGE]
test_clone_project_from_git_url
test_clone_project_invalid_url_raises_error [EDGE]
test_clone_project_auth_failure_raises_error [EDGE]
test_clone_project_sets_status_cloned
test_download_project_from_url
test_download_project_invalid_url_raises_error [EDGE]
test_download_project_creates_directory
test_project_status_transitions_are_valid
test_project_status_invalid_transition_raises_error [EDGE]
```

#### Code Manager (`tests/unit/test_code_manager.py`)
```
test_read_file_returns_content
test_read_file_nonexistent_raises_not_found [EDGE]
test_read_file_binary_returns_base64 [EDGE]
test_read_file_outside_project_raises_security_error [EDGE]
test_read_file_symlink_outside_project_raises_security_error [EDGE]
test_write_file_creates_new_file
test_write_file_updates_existing_file
test_write_file_creates_parent_directories
test_write_file_outside_project_raises_security_error [EDGE]
test_write_file_empty_content_allowed
test_write_file_very_large_content_handled [EDGE]
test_search_files_returns_matching_lines
test_search_files_regex_pattern
test_search_files_no_match_returns_empty
test_search_files_binary_files_skipped [EDGE]
test_diff_returns_unified_diff
test_diff_new_file_shows_all_additions
test_diff_deleted_file_shows_all_removals
test_diff_no_changes_returns_empty
test_list_files_returns_tree
test_list_files_respects_gitignore
test_list_files_hidden_files_option [EDGE]
```

#### Git Manager (`tests/unit/test_git_manager.py`)
```
test_status_returns_changed_files
test_status_clean_repo
test_status_untracked_files_included
test_add_stages_specific_files
test_add_nonexistent_file_raises_error [EDGE]
test_commit_creates_commit_with_message
test_commit_empty_staging_raises_error [EDGE]
test_commit_message_empty_raises_error [EDGE]
test_push_sends_to_remote
test_push_no_remote_raises_error [EDGE]
test_push_auth_failure_raises_error [EDGE]
test_push_with_retries_on_network_error [EDGE]
test_branch_creates_new_branch
test_branch_switch_existing
test_branch_duplicate_name_raises_error [EDGE]
test_branch_name_with_slashes_allowed
test_pr_create_returns_pr_url
test_pr_create_with_body
test_pr_merge_succeeds
test_pr_merge_with_conflicts_raises_error [EDGE]
test_pr_review_returns_comments
test_pr_review_no_comments_returns_empty
test_log_returns_commits
test_log_with_limit
test_log_empty_repo_returns_empty [EDGE]
test_diff_between_branches
test_actions_status_returns_workflow_runs
test_actions_logs_returns_output
test_actions_status_no_workflows_returns_empty [EDGE]
```

#### Runtime Manager (`tests/unit/test_runtime_manager.py`)
```
test_start_launches_nat_serve_subprocess
test_start_with_config_path
test_start_already_running_raises_error [EDGE]
test_start_invalid_config_raises_error [EDGE]
test_start_port_in_use_raises_error [EDGE]
test_stop_terminates_subprocess
test_stop_not_running_raises_error [EDGE]
test_stop_graceful_then_force [EDGE]
test_restart_stops_and_starts
test_status_returns_running_info
test_status_not_running_returns_stopped
test_logs_returns_recent_output
test_logs_with_line_limit
test_logs_streaming_yields_lines
test_health_check_returns_healthy
test_health_check_unhealthy_after_crash [EDGE]
test_start_captures_stderr [EDGE]
test_start_with_env_vars
test_only_one_app_running_at_a_time [EDGE]
test_start_new_app_stops_current_first [EDGE]
test_nat_eval_command_runs_and_returns_results
test_nat_start_command_alternative_to_serve
```

#### Test Runner (`tests/unit/test_test_runner.py`)
```
test_run_unit_tests_returns_results
test_run_integration_tests_returns_results
test_run_e2e_tests_returns_results
test_run_specific_test_file
test_run_specific_test_function
test_results_include_pass_fail_skip_counts
test_results_include_failure_details
test_results_include_duration
test_results_include_coverage_percentage
test_run_no_tests_found_returns_empty_results [EDGE]
test_run_syntax_error_in_test_reports_error [EDGE]
test_run_timeout_kills_process [EDGE]
test_run_with_markers_filter
test_parse_pytest_json_output
test_parse_pytest_xml_output
test_coverage_below_threshold_flagged
```

#### Debug Manager (`tests/unit/test_debug_manager.py`)
```
test_get_errors_returns_recent_errors
test_get_errors_no_errors_returns_empty
test_get_errors_filters_by_severity
test_get_logs_returns_filtered_logs
test_get_logs_with_level_filter
test_get_logs_with_time_range
test_get_logs_with_pattern_match
test_get_stack_trace_from_error
test_get_stack_trace_multiline_parsed [EDGE]
test_profiler_data_returns_metrics
test_profiler_data_no_session_raises_error [EDGE]
```

#### Deploy Manager (`tests/unit/test_deploy_manager.py`)
```
test_build_creates_deployable_artifact
test_build_missing_config_raises_error [EDGE]
test_build_invalid_config_raises_error [EDGE]
test_deploy_local_subprocess_starts
test_deploy_health_check_passes
test_deploy_health_check_fails_rolls_back [EDGE]
test_deploy_stops_previous_version_first
test_deploy_status_returns_info
test_deploy_no_artifact_raises_error [EDGE]
test_rollback_to_previous_version
test_rollback_no_previous_version_raises_error [EDGE]
test_deploy_with_docker_when_available
test_deploy_without_docker_uses_subprocess
test_self_restart_spawns_new_process [SELF]
test_self_restart_old_process_exits_cleanly [SELF]
test_self_restart_exits_with_restart_code [SELF]
```

#### Tool Orchestrator (`tests/unit/test_tool_orchestrator.py`)
```
test_execute_single_step_workflow
test_execute_multi_step_workflow
test_execute_step_failure_stops_workflow
test_execute_step_failure_with_retry
test_execute_parallel_steps
test_emit_event_on_step_completion
test_emit_event_on_workflow_failure
test_workflow_timeout [EDGE]
test_workflow_cancellation [EDGE]
test_workflow_with_conditional_steps
test_event_subscribers_notified
test_event_history_persisted
```

#### MCP Server (`tests/unit/test_mcp_server.py`)
```
test_server_registers_all_tools
test_server_tool_list_matches_spec
test_server_handles_tool_call_request
test_server_returns_tool_result
test_server_handles_unknown_tool_error [EDGE]
test_server_handles_malformed_request [EDGE]
test_server_registers_resources
test_server_handles_resource_read
test_server_resource_not_found_error [EDGE]
test_server_streamable_http_transport
test_server_jsonrpc_protocol_compliance
test_server_capabilities_negotiation
test_server_concurrent_requests [EDGE]
test_server_large_payload [EDGE]
test_server_well_known_endpoint
```

#### MCP Client (`tests/unit/test_mcp_client.py`)
```
test_client_connects_to_server
test_client_lists_available_tools
test_client_calls_tool
test_client_receives_tool_result
test_client_handles_connection_failure [EDGE]
test_client_handles_timeout [EDGE]
test_client_reconnects_after_disconnect [EDGE]
test_client_discovers_server_via_well_known
test_client_multiple_server_connections
test_client_reads_resource
test_client_resource_not_found_error [EDGE]
test_client_invalid_server_url_raises_error [EDGE]
test_client_retries_with_exponential_backoff [EDGE]
test_client_marks_server_degraded_after_failures [EDGE]
test_client_continues_with_remaining_servers_on_failure [EDGE]
test_client_periodic_health_check
test_client_recovers_degraded_server_on_health_check_pass
test_client_logs_connection_state_changes
```

#### OpenAPI Routes (`tests/unit/test_api_routes.py`)
```
# System
test_health_endpoint_returns_200
test_openapi_spec_endpoint_returns_valid_spec
test_all_endpoints_have_openapi_docs
test_mcp_well_known_endpoint_returns_discovery_info
test_error_responses_follow_rfc7807 [EDGE]
test_cors_headers_present
test_request_id_header_propagated

# Projects
test_list_projects_endpoint
test_create_project_endpoint
test_create_project_from_clone_url_endpoint
test_download_project_endpoint
test_create_project_invalid_body_returns_422 [EDGE]
test_get_project_endpoint
test_get_project_not_found_returns_404 [EDGE]
test_delete_project_endpoint

# Code
test_list_files_endpoint
test_read_file_endpoint
test_write_file_endpoint
test_search_files_endpoint
test_diff_files_endpoint

# Git
test_git_status_endpoint
test_git_commit_endpoint
test_git_push_endpoint
test_git_branch_endpoint
test_git_log_endpoint
test_git_actions_endpoint
test_git_pr_create_endpoint
test_git_pr_merge_endpoint
test_git_pr_reviews_endpoint

# Runtime
test_runtime_start_endpoint
test_runtime_stop_endpoint
test_runtime_status_endpoint
test_runtime_logs_endpoint

# Test
test_test_run_endpoint
test_test_results_endpoint

# Debug
test_debug_errors_endpoint
test_debug_logs_endpoint

# Deploy
test_deploy_build_endpoint
test_deploy_run_endpoint
test_deploy_status_endpoint

# WebSocket
test_websocket_connect_and_receive_events
test_websocket_invalid_project_returns_error [EDGE]
```

#### Data Models (`tests/unit/test_models.py`)
```
test_project_model_serialization
test_project_model_deserialization
test_project_model_validation_rejects_invalid [EDGE]
test_event_model_serialization
test_event_model_deserialization
test_event_type_enum_complete
test_project_status_enum_complete
test_project_status_transition_validation
```

#### Database Store (`tests/unit/test_db_store.py`)
```
test_create_tables_on_init
test_insert_project_and_retrieve
test_update_project_status
test_delete_project
test_list_projects_empty
test_list_projects_returns_all
test_insert_event_and_retrieve
test_query_events_by_project_id
test_query_events_by_type
test_query_events_by_time_range
test_events_are_append_only
test_concurrent_writes_dont_corrupt [EDGE]
test_database_file_created_at_configured_path
test_migrations_run_on_schema_change
```

### Property-Based Tests (`tests/property/`)

```
# test_models_property.py
test_project_roundtrip_serialization — any valid Project serializes and deserializes identically
test_event_roundtrip_serialization — any valid ATTEvent serializes and deserializes identically
test_project_id_always_unique — generated IDs never collide (large sample)
test_project_name_sanitization_idempotent — sanitize(sanitize(x)) == sanitize(x)

# test_code_manager_property.py
test_write_then_read_roundtrip — write(content) then read() returns content for any content
test_search_finds_written_content — write(content) then search(substring_of_content) finds it
test_path_traversal_never_escapes_project — for any path, code_manager rejects paths outside project

# test_git_manager_property.py
test_commit_message_preserved — any commit message is retrievable from log
test_branch_name_sanitization — any valid branch name roundtrips through create/list

# test_mcp_server_property.py
test_tool_call_response_always_valid_jsonrpc — any tool call returns valid JSON-RPC response
test_resource_uri_always_parseable — any registered resource has a parseable URI

# test_db_store_property.py
test_insert_then_retrieve_roundtrip — any valid Project/Event roundtrips through SQLite
test_event_ordering_preserved — events inserted in order are always retrieved in order

# test_mcp_client_property.py
test_client_never_crashes_on_server_failure — for any sequence of connect/disconnect events, client stays healthy
test_retry_backoff_always_increases — backoff intervals are monotonically increasing up to max
```

### Integration Tests (`tests/integration/`)

```
# test_project_lifecycle.py
test_create_project_then_list_includes_it
test_create_clone_start_stop_delete_lifecycle
test_create_project_then_read_default_files

# test_code_git_integration.py
test_write_file_then_git_status_shows_change
test_write_commit_push_workflow
test_diff_after_code_change

# test_runtime_integration.py
test_start_nat_serve_and_health_check
test_start_stop_start_lifecycle
test_logs_contain_startup_messages

# test_test_runner_integration.py
test_run_tests_on_sample_project
test_run_tests_reports_failure_correctly
test_coverage_report_generated

# test_mcp_integration.py
test_mcp_server_accepts_client_connection
test_mcp_client_calls_server_tool
test_mcp_roundtrip_tool_call_and_result
test_mcp_client_multi_server_connects_all
test_mcp_client_one_server_down_others_work [EDGE]
test_mcp_client_server_recovers_after_down [EDGE]

# test_api_integration.py
test_api_create_project_and_query
test_api_full_workflow_create_edit_test_commit
test_websocket_streaming_events
```

### End-to-End Tests (`tests/e2e/`)

```
# test_self_bootstrap.py [SELF]
test_att_registers_own_repo_as_project
test_att_reads_own_source_code [SELF]
test_att_runs_own_unit_tests [SELF]
test_att_creates_branch_on_own_repo [SELF]
test_att_edits_own_file_and_commits [SELF]
test_att_creates_pr_on_own_repo [SELF]
test_att_full_self_modification_cycle [SELF]
test_att_rollback_after_failed_self_test [SELF] [EDGE]
test_att_rejects_change_that_breaks_tests [SELF] [EDGE]
test_att_concurrent_self_modifications_serialize [SELF] [EDGE]
test_att_merges_autonomously_on_green_ci [SELF]
test_att_polls_github_actions_for_ci_status [SELF]
test_att_handles_github_api_unreachable_during_poll [SELF] [EDGE]
test_att_ci_poll_timeout_aborts_merge [SELF] [EDGE]
test_att_redeploys_via_subprocess_restart [SELF]
test_att_health_check_after_redeploy [SELF]
test_att_auto_rollback_on_health_check_failure [SELF] [EDGE]
test_att_audit_log_records_all_autonomous_actions [SELF]
test_att_can_request_human_review_for_high_risk_change [SELF]

# test_web_ui.py (Playwright)
test_dashboard_loads_and_shows_projects
test_create_project_via_ui
test_open_project_shows_file_tree
test_edit_file_via_code_editor
test_run_tests_via_ui_and_see_results
test_view_git_status_and_diff
test_create_commit_via_ui
test_start_stop_runtime_via_ui
test_view_logs_streaming
test_deploy_via_ui
test_chat_view_sends_message_and_receives_response
test_settings_configure_mcp_server

# test_nat_app_creation.py (Phase 2 — not needed for self-bootstrap)
test_create_nat_app_from_template
test_configure_nat_app_via_ui
test_run_nat_app_and_interact
test_debug_nat_app_with_profiler
test_deploy_nat_app_locally

# test_mcp_e2e.py
test_external_mcp_client_connects_to_att
test_external_mcp_client_creates_project
test_external_mcp_client_full_workflow
test_att_as_mcp_client_uses_external_tool
test_mcp_tool_discovery_via_well_known
test_mcp_client_failover_when_server_unreachable
test_att_operates_with_degraded_mcp_servers
```

---

## Resolved Decisions

All architectural questions have been resolved. These decisions are binding for implementation.

| # | Decision | Resolution |
|---|----------|-----------|
| 1 | **NAT-UI Integration** | No fork. Use NAT-UI as a dependency and include custom ATT-specific code alongside it. |
| 2 | **Code Editor** | Ace Editor. |
| 3 | **NAT Version** | 1.4.x (`nvidia-nat`). |
| 4 | **MCP SDK** | Use NAT's built-in MCP integration (`nat.mcp`). |
| 5 | **Database** | SQLite for local mode. |
| 6 | **Process Isolation** | Subprocess (direct `nat serve` and other NAT CLI commands). |
| 7 | **Self-Modification Safety** | Mandatory passing tests + auto-rollback on health check failure. Sufficient for now. |
| 8 | **CI Feedback** | Poll GitHub Actions API (not webhooks). |
| 9 | **Human Approval** | Fully autonomous — can merge on green CI without human approval. Can still *choose* to request review. |
| 10 | **MCP Client Servers** | Multi-server support from Phase 1. High priority due to different capabilities and availability levels. |
| 11 | **A2A Protocol** | Defer to Phase 2 unless it speeds up bootstrapping. |
| 12 | **Offline Mode** | No explicit offline mode. Account for services being down/unreachable (retry, degrade gracefully). |
| 13 | **NAT App Testing** | Use TDD. Direct TDD being used. Ensure tests pass. Not advisory — tests must pass. |
| 14 | **Docker Dependency** | Docker not required. Primary mode: direct subprocess with `nat serve` and other NAT facilities (`nat start`, `nat eval`, etc.). |
| 15 | **Multi-App** | Single managed NAT app at a time (ATT itself always runs). No multi-app port allocation needed. |
| 16 | **Log Retention** | Manual cleanup. Logs retained until user deletes them. |

## Open Questions

> None remaining. All decisions resolved. Ready for implementation.

---

## Priority Order for Implementation

The fastest path to self-bootstrapping:

```
Week 1:  P01 (skeleton) + P02 (CI) + P03 (models + db/store)
Week 2:  P04 (project mgr) + P05 (code mgr) + P06 (git mgr) — in parallel
Week 3:  P07 (runtime mgr) + P08 (test runner) + P10 (deploy mgr) — in parallel
Week 4:  P11 (orchestrator) + P12 (MCP server) + P14 (OpenAPI routes)
Week 5:  P13 (MCP client — multi-server) + P15 (web UI — minimal)
Week 6:  P16 (self-bootstrap) + stabilization
```

After self-bootstrapping is achieved, ATT can assist in building its own remaining features (Phase 2 and Phase 3), dramatically accelerating development.

---

## Success Criteria

### Phase 0 Complete When:
- [ ] `uv run pytest tests/unit/` passes with > 80% coverage
- [ ] `ruff check` and `mypy --strict` pass with zero errors
- [ ] GitHub Actions Tier 1 runs in < 2 minutes
- [ ] All 8 core managers have passing interface tests

### Phase 1 (Self-Bootstrap) Complete When:
- [ ] ATT can read/write its own source files via the web UI
- [ ] ATT can run its own test suite and display results in the UI
- [ ] ATT can create a branch, make a change, commit, and push
- [ ] ATT can create a PR and verify CI passes
- [ ] ATT can merge a PR after CI passes
- [ ] ATT can rebuild and redeploy itself
- [ ] An external MCP client (e.g., Claude Code) can connect to ATT and perform all of the above
- [ ] All operations are available via both the REST API and MCP tools
- [ ] The full cycle works end-to-end: change → test → PR → CI → merge → deploy

### Phase 2 Complete When:
- [ ] A user can create a new NAT app from template, configure it, run it, test it, debug it, and deploy it — entirely through the web UI
- [ ] Created apps have TDD test suites with unit, integration, property, and e2e tests
- [ ] Created apps have their own CI pipelines

### Phase 3 Complete When:
- [ ] Multi-user with authentication works
- [ ] Cloud deployment (K8s) works
- [ ] OpenTelemetry traces and metrics are flowing
- [ ] Security audit passes with no critical findings
