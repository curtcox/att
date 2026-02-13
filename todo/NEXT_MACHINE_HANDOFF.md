# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `2e369f8985b9ea046a8e6e39af4301dea104b7a9`
- Last commit: `2e369f8 2026-02-13 07:18:08 -0600 Follow AGENTS and handoff steps`
- Working tree at handoff creation: clean
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`184 passed`)

## Recent Delivered Work
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

## Active Next Slice (Recommended)
Continue `P12/P13` scripted-controls convergence hardening:
1. Extend scripted precedence parity to `resources/read` initialize stage:
   - add an integration scenario proving scripted `initialize: ok` for `resources/read` overrides set-based initialize timeout toggles (mirroring existing tool-path precedence coverage).
   - assert deterministic correlation/filter behavior (`request_id`, `correlation_id`, `limit`) and no degraded transition for the overridden attempt.
2. Add API-level mixed-script isolation regression:
   - add an integration scenario with mixed scripts on `primary` vs `backup` across `tools/call` and `resources/read` in sequence.
   - assert each request consumes only its targeted server/method script queue and leaves unrelated queues intact until exercised.

Suggested implementation direction:
- Keep manager as aggregation/source-of-truth and route logic thin.
- Reuse existing fake NAT session factories and shared clock/helper modules rather than introducing new ad-hoc transport scaffolding.
- Preserve current event/filter semantics and correlation determinism.

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
