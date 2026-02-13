# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `2b872c898e8fe7dc264a5fa5282d192d19001b52`
- Last commit: `2b872c8 2026-02-13 09:01:42 -0600 Refactor retry-window API integration test scaffolding`
- Working tree at handoff creation: dirty (`unreachable-transition diagnostics helper extraction`)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`225 passed`)

## Recent Delivered Work
- Reduced duplicated unreachable-transition primary diagnostics assertions with shared helper wiring:
  - added shared integration helper to assert per-request primary invocation/connection diagnostics for unreachable-transition sequences based on explicit request-id order, method, expected phases, and expected status transitions.
  - migrated both tool and resource unreachable-transition parity tests to this shared helper while keeping explicit expected phase/status vectors at each call site.
  - preserved explicit per-test transport call-order literals (`fifth_slice`, `observed_call_order`) and existing subsequence parity assertions unchanged.
- Reduced duplicated retry-window API scenario scaffolding across gating/unreachable/simultaneous flows:
  - added shared retry-window test harness setup helper for cluster manager/clock/factory/client creation + server registration.
  - added shared invoke-construction helper and shared progression helpers for retry-window gating and simultaneous unreachable-reopen paths.
  - migrated tool/resource retry-window gating tests, tool/resource unreachable-transition tests, and simultaneous unreachable-reopen tests to use shared helpers while preserving explicit per-request diagnostics assertions and explicit transport call-order literals in each test.
- Added API-level simultaneous `UNREACHABLE` retry-window reopen parity coverage across tool/resource invoke paths:
  - added a parametrized integration regression covering both `/api/v1/mcp/invoke/tool` and `/api/v1/mcp/invoke/resource` under both preferred-order permutations.
  - assertions verify closed-window no-candidate behavior (503 + no invocation events + no transport calls), then deterministic preferred-order `initialize_start` attempt sequencing after simultaneous retry-window reopen.
  - assertions preserve helper-aligned transport semantics by checking only successful transport call literals and validating phase-start/transport subsequence parity plus deterministic diagnostics filters (`server`, `method`, `request_id`, `correlation_id`, `limit`).
- Completed call-order helper migration for remaining integration parity scenarios and added simultaneous unreachable reopen ordering matrix:
  - migrated remaining call-order parity integrations (`scripted call-order`, `repeated same-server initialize-cache`, and `force-reinitialize trigger`) to shared helpers: `collect_invocation_events_for_requests`, `expected_call_order_from_phase_starts`, and `assert_call_order_subsequence`.
  - removed repeated per-test request-id event aggregation and cursor-subsequence loops while keeping explicit observed transport-call literals unchanged.
  - added helper-level matrix coverage where both servers become `UNREACHABLE` with closed retry windows, then reopen simultaneously; assertions verify preferred-order candidate attempts via invocation `initialize_start` phase sequence and verify transport-call ordering semantics for successful initialize/invoke progression.
- Consolidated retry-window call-order subsequence helper usage and expanded non-retryable backup matrix coverage:
  - added shared convergence helpers to collect invocation events by request id, derive phase-start call-order tuples, and assert observed transport-call subsequence parity.
  - migrated retry-window gating and unreachable-transition API call-order assertions for both `tools/call` and `resources/read` to the shared subsequence helpers, removing repeated test-local cursor-loop scaffolding.
  - added helper-level unit matrix coverage for primary unreachable + backup degraded/unreachable retry-window-closed combinations, asserting deterministic no-candidate failure and deterministic backup re-entry ordering (`initialize` before invoke) after retry-window reopen.
- Reduced unreachable-transition sequence duplication and expanded backup reinitialize parity:
  - extracted shared integration helper scaffolding for unreachable-transition request progression so `tools/call` and `resources/read` API regressions reuse the same first-failover/closed-window/forced-unreachable/skip/re-entry flow while keeping per-request diagnostics-filter assertions explicit.
  - added helper-level unit coverage asserting degraded backup reinitialize call-order parity (`initialize` before invoke) when primary is forced unreachable, with paired checks for both `tools/call` and `resources/read`.
  - retained clock-driven progression and transport-order centric assertions with no direct retry-window state mutation.
- Added unreachable-transition retry-window parity for `tools/call` with shared failed-request request-id recovery:
  - added API-level `/api/v1/mcp/invoke/tool` unreachable-transition regression that mirrors healthy-first ordering constraints (primary initialize timeout -> backup serve -> forced second primary initialize timeout -> unreachable skip -> primary re-entry).
  - assertions preserve deterministic diagnostics filter behavior (`server`, `method`, `request_id`, `correlation_id`, `limit`) and transport/invocation call-order subsequence parity across the full request sequence.
  - extracted shared invocation-event delta helper for failed-request request-id recovery and applied it to both `tools/call` and `resources/read` unreachable-transition regressions.
- Added unreachable-transition retry-window parity coverage for `resources/read` under healthy-first candidate ordering:
  - helper-level matrix now drives deterministic primary `initialize` timeout transitions from degraded -> unreachable across both invoke methods while preserving backup skip/re-entry ordering.
  - API-level `/api/v1/mcp/invoke/resource` regression now forces a second primary initialize timeout via controlled backup retry-window state, verifies closed-window skip while backup serves requests, and asserts deterministic primary re-entry call order (`initialize` then `resources/read`).
  - diagnostics assertions now include deterministic failed-request request-id recovery from invocation-event delta slicing so invocation/connection filter checks remain request-correlated even for expected 503 transitions.
- Added lightweight manager clock seam for deterministic retry/backoff/freshness behavior in tests:
  - `MCPClientManager` now accepts optional `now_provider` and uses it for retry-window checks, initialization freshness gating, invocation event timestamps, and adapter freshness classification.
  - default behavior remains unchanged (`datetime.now(UTC)` when `now_provider` is not supplied).
  - added unit coverage confirming `should_retry()` consumes injected clock when `now` is omitted.
- Migrated retry-window convergence coverage to clock-driven progression:
  - removed direct `next_retry_at` mutation in the convergence integration scenario; progression now uses `clock.advance(...)` + manager APIs (`record_check_result`).
  - retained deterministic failover/recovery assertions across timeout, retry-window skip, unreachable transition, and recovery initialize.
  - preserved correlation/event determinism checks and freshness assertions after recovery.
- Expanded clock-seam adoption in remaining mixed-state tests:
  - unit and integration mixed-state recovery/fallback tests now use injected test clocks for retry-window progression instead of direct retry-window state mutation.
  - retained existing preferred-order fallback and status-transition assertions while reducing coupling to server internals.
- Extended convergence matrix with clock-driven capability snapshot timing assertions:
  - convergence scenario now explicitly verifies server-local `capability_snapshot.captured_at` retention on failure paths and replacement on recovery initialize.
  - assertions remain request-correlated and deterministic under controlled clock progression.
- Consolidated duplicated MCP test clock helpers into shared support:
  - added shared helper module `tests/support/mcp_helpers.py` and converted unit/integration MCP tests to consume `MCPTestClock`.
  - added package markers (`tests/__init__.py`, `tests/support/__init__.py`) so shared test support imports resolve consistently.
- Expanded stage-specific timeout convergence matrix with explicit paired scenarios:
  - replaced single mixed-stage convergence path with paired `initialize` vs `invoke` timeout scenarios under the same clock progression and preferred order.
  - assertions now explicitly capture stage-specific retry/backoff/status deltas and capability snapshot timing behavior (retention vs replacement) while preserving deterministic correlation/event checks.
- Reduced duplicated MCP integration transport scaffolding beyond clocks:
  - extracted reusable fake NAT transport/session helpers into `tests/support/mcp_nat_helpers.py` (`APIFakeNatSessionFactory`, `ClusterNatSessionFactory`, and session/model helpers).
  - migrated `tests/integration/test_api_mcp.py` to import shared helpers and removed duplicated test-local session factory/session model classes.
- Extended stage-paired convergence diagnostics filtering coverage:
  - for each timeout stage, added explicit deterministic assertions for `/api/v1/mcp/invocation-events` filtering by `server` + `request_id` + `limit`.
  - for each timeout stage, added explicit deterministic assertions for `/api/v1/mcp/events` filtering by `server` + `correlation_id` + `limit`.
  - kept server-local capability snapshot timing assertions and preferred-order failover/recovery determinism intact.
- Reduced remaining duplicated NAT unit transport scaffolding:
  - added shared `FakeNatSession` and `FakeNatSessionFactory` to `tests/support/mcp_nat_helpers.py`.
  - migrated `tests/unit/test_mcp_client.py` NAT adapter/session-control coverage to shared helpers and removed duplicated test-local helper classes.
- Extended diagnostics filter parity to `resources/read` failover/recovery:
  - added integration coverage asserting `/api/v1/mcp/invocation-events` filters (`server`, `method`, `request_id`, `limit`) for correlated `resources/read` failover and recovery requests.
  - added matching `/api/v1/mcp/events` filter assertions (`server`, `correlation_id`, `limit`) for the same request-correlation flows.
- Expanded shared NAT cluster helper controls for resource-read invoke failures:
  - `ClusterNatSessionFactory` now supports `fail_on_resource_reads` and `fail_on_timeout_resource_reads`.
  - `ClusterNatSession.read_resource()` now honors these controls to simulate deterministic invoke-stage resource failures/timeouts.
- Added stage-paired `resources/read` retry-window convergence coverage:
  - added paired `initialize`-timeout vs `invoke`-timeout convergence scenarios for `/api/v1/mcp/invoke/resource` under controlled clock progression.
  - assertions preserve stage-specific retry/unreachable behavior, server-local capability snapshot timing (retention vs replacement), and deterministic correlated diagnostics-filter semantics.
- Reduced stage-matrix assertion duplication:
  - extracted shared convergence helpers into `tests/support/mcp_convergence_helpers.py`.
  - migrated stage-paired `tools/call`/`resources/read` convergence tests to shared phase/filter assertion helpers.
- Added scripted mixed-method flapping controls and coverage:
  - `ClusterNatSessionFactory` now supports ordered per-server/per-method scripted actions (`ok`/`timeout`/`error`) via `set_failure_script(...)`.
  - added integration coverage that validates deterministic fallback order and correlation streams across scripted `tools/call` and `resources/read` flapping without manual failure-set toggling between calls.
- Extended scripted-failure realism to initialize stage:
  - `ClusterNatSession.initialize()` now consumes scripted actions for method `initialize` before set-based timeout toggles.
  - integration coverage validates script-precedence semantics (`initialize: ok` overrides set timeout) and scripted initialize-timeout failover behavior.
- Expanded convergence-helper adoption in diagnostics tests:
  - migrated remaining diagnostics-filter assertions in `tests/integration/test_api_mcp.py` to `tests/support/mcp_convergence_helpers.py`.
  - preserved existing filter semantics (`server`, `method`, `request_id`, `correlation_id`, `limit`) while reducing repeated test-local assertion boilerplate.
- Added focused unit coverage for scripted helper semantics:
  - added unit tests for `ClusterNatSessionFactory.set_failure_script/consume_failure_action` covering ordering, unsupported actions, script exhaustion, and fallback to set-based toggles.
  - explicit method-key checks cover `initialize`, `tools/call`, and `resources/read`.
- Added scripted `error` action convergence coverage:
  - integration coverage now exercises scripted `error` at initialize-stage and invoke-stage paths, asserting stable `transport_error` classification and deterministic failover/correlation behavior.
- Extended scripted `error` convergence parity to `resources/read`:
  - added paired initialize/invoke scripted-error scenarios for `/api/v1/mcp/invoke/resource`, asserting deterministic failover order, stable `transport_error` classification, and correlated request behavior.
  - added deterministic invocation/connection filter assertions for correlated `resources/read` requests (`server`, `method`, `request_id`, `correlation_id`, `limit`).
- Added helper-level scripted-failure isolation coverage:
  - added unit assertions that per-server/per-method scripts remain isolated under shared `ClusterNatSessionFactory` state.
  - added mixed-script regression checks across `primary` and `backup` so consuming one key does not mutate unrelated script queues.
- Extended scripted initialize precedence parity to `resources/read`:
  - added integration coverage proving scripted `initialize: ok` for `resources/read` overrides set-based initialize timeout toggles and keeps the correlated request free of degraded transitions.
  - retained deterministic diagnostics-filter coverage (`server`, `method`, `request_id`, `correlation_id`, `limit`) and added fallback verification after adapter invalidation when set-based timeout toggles reapply.
- Added API-level mixed-script isolation regression:
  - added integration sequencing across `tools/call` and `resources/read` with mixed scripts on `primary` and `backup`.
  - assertions now verify only targeted server/method script queues are consumed per request while unrelated queues remain intact until exercised.
- Added API-level mixed initialize+invoke script isolation coverage:
  - added integration coverage that combines per-server `initialize` scripts with `tools/call` and `resources/read` scripts in one deterministic scenario across `primary` and `backup`.
  - assertions verify initialize-script queue consumption is isolated from invoke-script queues while preserving deterministic failover order and correlated diagnostics filters.
- Added initialize-script exhaustion regression at API level:
  - added integration coverage proving scripted initialize override depletion falls back to set-based initialize timeout toggles after adapter invalidation.
  - assertions verify fallback degradation/correlation behavior and confirm unrelated invoke method script queues remain untouched until explicitly invoked.
- Added helper/API call-order parity coverage for mixed scripted failover:
  - added unit coverage asserting deterministic `ClusterNatSessionFactory.calls` ordering across mixed `initialize` + `tools/call` + `resources/read` scripted actions for paired `primary`/`backup` failover.
  - added API integration coverage that cross-checks `factory.calls` against invocation-event `initialize_start`/`invoke_start` ordering for one mixed scripted `tools/call` + `resources/read` sequence.
  - call-order comparison now intentionally uses subsequence semantics so event streams that include stage markers without matching transport calls remain deterministic and non-flaky.
- Added initialize-cache call-order parity coverage for repeated requests:
  - added unit coverage proving repeated same-server invokes skip extra transport `initialize` calls until explicit adapter invalidation, with paired checks for both `tools/call` and `resources/read`.
  - unit assertions now also verify invalidation forces exactly one subsequent transport `initialize` and rotates to a new adapter session id.
  - added API coverage for repeated same-server `tools/call` + `resources/read` requests without invalidation, asserting call-order remains one `initialize` followed by invoke methods while invocation-phase start streams remain aligned via subsequence parity.
  - retained deterministic diagnostics-filter checks (`server`, `method`, `request_id`, `correlation_id`, `limit`) per request in the new API scenario.
- Added force-reinitialize trigger call-order parity coverage:
  - added helper-level unit coverage asserting stale-expiry and non-healthy-status trigger paths each force transport `initialize` before the next invoke.
  - unit coverage includes paired `tools/call` and `resources/read` assertions so trigger parity remains method-consistent.
  - added API-level repeated-request regression that injects stale-expiry and degraded-status transitions between calls and verifies transport call-order contains the expected additional `initialize` calls.
  - retained deterministic diagnostics-filter assertions per request and preserved invocation-phase to transport-call subsequence parity checks in the new API scenario.
- Added retry-window gating call-order parity coverage:
  - added helper-level unit coverage asserting degraded and unreachable retry-window-closed servers are skipped without primary transport calls and re-enter deterministically once retry windows reopen.
  - unit assertions include paired `tools/call` and `resources/read` checks and explicit re-entry call-order expectations (`initialize` before invoke).
  - added API-level regression covering timeout -> closed retry window skip -> retry-window reopen while backup serves requests.
  - API assertions now cross-check transport call order against invocation-event `initialize_start`/`invoke_start` phase streams via subsequence parity and keep deterministic diagnostics-filter checks (`server`, `method`, `request_id`, `correlation_id`, `limit`) per request.
- Extended retry-window parity coverage for `resources/read` and backup-state matrix behavior:
  - added helper-level `resources/read` matrix coverage distinguishing backup non-retryable degraded vs unreachable states under mixed preferred ordering before primary re-entry.
  - added API-level `/api/v1/mcp/invoke/resource` retry-window call-order regression mirroring timeout -> closed retry-window skip -> retry-window reopen while backup serves requests.
  - preserved deterministic diagnostics-filter checks and invocation-phase/transport-call subsequence parity assertions per request.

## Active Next Slice (Recommended)
Continue `P12/P13` test-structure hardening by reducing remaining duplicated unreachable-transition call-order literals:
1. Extract shared call-order literal helpers for tool/resource unreachable-transition tests:
   - factor repeated `fifth_slice` and full `observed_call_order` literal blocks into shared helper(s) parameterized by `method`.
   - keep explicit expected tuples visible at or near call sites so ordering intent remains auditable.
2. Preserve parity semantics and diagnostics determinism:
   - keep existing request-correlated invocation/connection diagnostics assertions in place.
   - retain `assert_call_order_subsequence(...)` usage and do not assume one-to-one mapping between `initialize_start` events and transport `initialize` entries.

Suggested implementation direction:
- Scope edits to `tests/integration/test_api_mcp.py` and avoid production code changes.
- Reuse existing helper/harness structures introduced in recent slices instead of adding new ad-hoc setup paths.
- Run full validation and update both plan docs after changes.

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
- `tests/support/mcp_convergence_helpers.py`
- `tests/support/mcp_nat_helpers.py`
- `src/att/api/deps.py`

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (release-source adapter chain + failure-class/deployment-context rollback policy matrix delivered; remaining work is deeper production rollout hardening).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
