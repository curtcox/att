# Next Machine Handoff

## Snapshot
- Date: `2026-02-14`
- Branch: `main`
- HEAD: `1aadebf94ab09017d970ae45efb7d34255005c33`
- Last commit: `1aadebf 2026-02-14 08:35:03 -0600 - Reuse primary timeout setup-step vector`
- Working tree at handoff creation: clean
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`237 passed`)

## Recent Delivered Work
- See done for older completed slices:
  - `/Users/curt/me/att/done/next_machine_handoff_recent_delivered_work_archive_2026-02-13.md`

- Completed failure-script state-check helper assertion reuse in nearby cluster NAT helper validation coverage:
  - added local unit-test helper `_assert_unit_test_failure_script_state_snapshot(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated failure-script state-check assertion blocks in `test_cluster_nat_failure_script_isolation_across_servers_and_methods` to helper-driven form while keeping setup literals and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Completed terminal failure-script consume-state helper assertion reuse in nearby cluster NAT helper validation coverage:
  - added local unit-test helper `_assert_unit_test_failure_script_terminal_state(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated post-exhaustion consume-state assertions (`is None`) in `test_cluster_nat_failure_script_isolation_across_servers_and_methods` to helper-driven form while keeping setup literals and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Completed single-method failure-script consume-state helper assertion reuse in nearby cluster NAT helper validation coverage:
  - added local unit-test helper `_assert_unit_test_failure_script_method_exhausted(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated single-method post-exhaustion consume-state assertions in `test_cluster_nat_failure_script_order_and_validation` to helper-driven form while keeping setup literals and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Completed non-terminal failure-script consume-action helper assertion reuse in nearby cluster NAT helper validation coverage:
  - added local unit-test helper `_assert_unit_test_failure_script_consumed_action(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated non-terminal consume-action assertions in `test_cluster_nat_failure_script_order_and_validation` and `test_cluster_nat_failure_script_isolation_across_servers_and_methods` to helper-driven form while keeping setup literals and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Completed NAT transport failure/category matrix constant reuse in unit adapter parity coverage:
  - added local unit-test constant `UNIT_TEST_NAT_CATEGORY_MAPPING_FAILURE_MATRIX` in `tests/unit/test_mcp_client.py`.
  - migrated the inline `("failure", "category")` parametrize matrix in `test_nat_transport_adapter_category_mapping_parity` to constant-driven form.
  - kept server-name setup literals and transport payload literals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Completed residual NAT endpoint URL literal cleanup in unit MCP client coverage:
  - added local unit-test constant `UNIT_TEST_NAT_SERVER_URL`.
  - migrated remaining inline NAT endpoint URL literals in adapter unit coverage (`ExternalServer(..., url="http://nat.local")` and `manager.register("nat", "http://nat.local")`) to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Completed residual adapter request-id literal cleanup in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_NAT_INITIALIZE_REQUEST_ID`, `UNIT_TEST_NAT_INITIALIZED_NOTIFICATION_REQUEST_ID`, and `UNIT_TEST_NAT_RESOURCE_READ_REQUEST_ID`.
  - migrated remaining inline adapter request-id literals (`"init-1"`, `"init-notify"`, and `"resource-1"`) to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Completed residual transport-fixture request literal cleanup in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_NAT_TOOL_REQUEST_ID`, `UNIT_TEST_HTTP_METHOD_POST`, and `UNIT_TEST_NAT_MCP_ENDPOINT`.
  - migrated remaining inline NAT transport fixture request literals (`"tool-1"`, `"POST"`, and `"http://nat.local/mcp"`) to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Completed residual transport-category mapping literal cleanup in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_INVALID_PAYLOAD_ERROR_CATEGORY` and `UNIT_TEST_ERROR_BAD_STATUS`.
  - migrated remaining inline category-mapping literals in transport parity coverage (`httpx.HTTPStatusError("bad status", ...)` plus `"network_timeout"`, `"http_status"`, and `"invalid_payload"` category labels) to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Completed residual transport-category fixture literal cleanup in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_ERROR_TIMED_OUT` and `UNIT_TEST_ERROR_BAD_PAYLOAD`.
  - migrated remaining inline fixture message literals in transport mapping coverage (`httpx.ReadTimeout("timed out")` and `ValueError("bad payload")`) to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Completed residual RPC error-message literal cleanup in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_ERROR_RPC_DOWN`, `UNIT_TEST_ERROR_RPC_FAILURE`, and `UNIT_TEST_ERROR_RPC_FAILURE_WITH_PREFIX`.
  - migrated remaining inline RPC error payload message literals and adjacent assertion text (`"rpc down"`, `"rpc failure"`, and `"rpc error: rpc failure"`) to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended call-vector label constant reuse in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_SESSION_CALL_ENTRY_LABEL` and `UNIT_TEST_RESOURCE_CALL_ENTRY_LABEL`.
  - migrated remaining inline tuple-label literals (`"session"` and `"resource"`) in session-call assertion vectors to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended full projects-URI constant reuse across resource paths in unit MCP client coverage:
  - migrated remaining inline `"att://projects"` literals in transport payload setup/assertions and resource-helper paths to `UNIT_TEST_PROJECTS_URI` in `tests/unit/test_mcp_client.py` (the literal now appears only in constant definition).
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended full project-list tool-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `"att.project.list"` literals in transport payload setup/assertions and invoke-call arguments to `UNIT_TEST_PROJECT_LIST_TOOL_NAME` in `tests/unit/test_mcp_client.py` (the literal now appears only in constant definition).
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended tool-name constant reuse for invoke paths in unit MCP client coverage:
  - added local unit-test constant `UNIT_TEST_PROJECT_LIST_TOOL_NAME` and migrated repeated inline `invoke_tool("att.project.list", ...)` call arguments to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended resource-URI constant reuse in unit MCP client coverage:
  - migrated remaining inline `read_resource("att://projects", ...)` call arguments to `read_resource(UNIT_TEST_PROJECTS_URI, ...)` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended full `should_retry(...)` terminal server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `should_retry("terminal", now=...)` call arguments to `should_retry(UNIT_TEST_TERMINAL_SERVER, now=...)` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended `should_retry(...)` server-name constant reuse in unit MCP client coverage:
  - migrated inline `should_retry("terminal")` call arguments to `should_retry(UNIT_TEST_TERMINAL_SERVER)` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended final `record_check_result(...)` server-name constant reuse in unit MCP client coverage:
  - added local unit-test constant `UNIT_TEST_TERMINAL_SERVER` and migrated the remaining inline `record_check_result("terminal", ...)` call arguments to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended `record_check_result(...)` server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `record_check_result(...)` server-name arguments with existing constants (`"primary"`, `"backup"`, `"degraded"`, `"github"`, `"a"`, `"b"`) to `UNIT_TEST_*` constants in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended remaining state-inspection server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `manager.get("primary")`, `manager.get("backup")`, and `manager.get("recovered")` call arguments to `UNIT_TEST_PRIMARY_SERVER`, `UNIT_TEST_BACKUP_SERVER`, and `UNIT_TEST_RECOVERED_SERVER` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended state-inspection accessor server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `manager.get("codex")` and `manager.get("github")` call arguments to `UNIT_TEST_CODEX_SERVER` and `UNIT_TEST_GITHUB_SERVER` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended initialize/list-filter server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `initialize_server("codex")`, `initialize_server("github")`, and `list_adapter_sessions(server_name="c")` call arguments to constants (`UNIT_TEST_CODEX_SERVER`, new `UNIT_TEST_GITHUB_SERVER`, and `UNIT_TEST_SERVER_C`) in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Extended adapter-scoped helper server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `adapter.session_diagnostics("nat")`, `adapter.invalidate_session("nat")`, and `list_adapter_sessions(server_name="nat")` call arguments to `UNIT_TEST_NAT_SERVER` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- Standardized snapshot-refresh process trigger and shortcut:
  - updated `/Users/curt/me/att/AGENTS.md` to require handoff snapshot refresh after validation using `./scripts/update_handoff_snapshot.sh --pytest-passed <N>` (or shortcut form).
  - added `/Users/curt/me/att/Makefile` with `make snapshot PASSED=<pytest_pass_count>` shortcut that invokes the updater script.
  - preserves product/runtime behavior unchanged while making process-trial adoption repeatable and explicit.

- Added process-change proposal doc and started two concrete trials:
  - added `/Users/curt/me/att/todo/proposed_process_changes.md` capturing the six proposed process changes and marking trial picks.
  - trial 1: added `/Users/curt/me/att/scripts/update_handoff_snapshot.sh` to auto-update handoff snapshot fields (`Date`, `Branch`, `HEAD`, `Last commit`, working-tree state) plus optional pytest pass count (`--pytest-passed`).
  - trial 2: extended `/Users/curt/me/att/tests/unit/test_docs_guardrails.py` with `test_master_plan_size_guardrail` and `MAX_MASTER_PLAN_LINES = 1300`, complementing the existing handoff-size guardrail.
  - preserved product/runtime behavior unchanged while adding CI-visible planning-file guardrails and a repeatable snapshot-maintenance utility.

- Added automated handoff-size guardrail test coverage:
  - added new unit test `/Users/curt/me/att/tests/unit/test_docs_guardrails.py` with `test_next_machine_handoff_size_guardrail`.
  - guardrail enforces `todo/NEXT_MACHINE_HANDOFF.md` max size of `250` lines and fails with explicit archive guidance (`done/`) when exceeded.
  - preserves runtime/product behavior unchanged while adding CI-visible alerting for handoff growth.

- Extended invocation-filter server-name constant reuse in unit MCP client coverage:
  - migrated the remaining diagnostics filter argument literal `list_invocation_events(server="primary", ...)` to `UNIT_TEST_PRIMARY_SERVER` in `tests/unit/test_mcp_client.py`.
  - preserved diagnostics filter scope (`server`, `method`, `request_id`), request sequencing, timeout-toggle setup flow, and method-branch conditionals unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Extended timeout-toggle server-name constant reuse in unit MCP client coverage:
  - migrated remaining timeout-toggle setup literals `factory.fail_on_timeout_initialize.add("primary")`, `factory.fail_on_timeout_tool_calls.add("primary")`, and `factory.fail_on_timeout_resource_reads.add("primary")` to `UNIT_TEST_PRIMARY_SERVER` in `tests/unit/test_mcp_client.py`.
  - preserved timeout-toggle setup flow, failure-script vectors, preferred-order inputs, and method-branch conditionals unchanged while reducing setup-side server literal duplication.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Extended `set_failure_script` server-name constant reuse in unit MCP client coverage:
  - migrated the remaining inline `set_failure_script("primary", method, ...)` setup wiring in retry-window resource re-entry coverage to `UNIT_TEST_PRIMARY_SERVER`.
  - preserved failure-script action vectors, preferred-order inputs, setup sequencing, and method-branch conditionals unchanged while reducing setup-side server literal duplication.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Extended `set_failure_script` method constant reuse in unit MCP client coverage:
  - migrated remaining inline `set_failure_script(..., "initialize" | "tools/call" | "resources/read", ...)` setup literals in `tests/unit/test_mcp_client.py` to existing method constants (`UNIT_TEST_INITIALIZE_METHOD`, `UNIT_TEST_TOOLS_CALL_METHOD`, `UNIT_TEST_RESOURCES_READ_METHOD`).
  - preserved failure-script action vectors, preferred-order inputs, setup sequencing, and method-branch conditionals unchanged while reducing setup-side method literal duplication.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Extended mixed-method call-order collection helper reuse in unit MCP client coverage:
  - added local unit-test helper `_unit_test_collect_mixed_method_call_order_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated the remaining inline mixed-method call-order collection comprehension (`initialize` + `tools/call` + `resources/read`) in scripted failover call-order assertions to helper-driven form while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Extended method-scoped re-entry pair collection helper reuse in unit MCP client coverage:
  - migrated remaining inline resource retry re-entry call-order pair collection in `tests/unit/test_mcp_client.py` to `_unit_test_collect_reentry_call_order_slice(...)`.
  - replaced repeated list-comprehension scaffolding `[(server, method) for ... if method in {UNIT_TEST_INITIALIZE_METHOD, UNIT_TEST_RESOURCES_READ_METHOD}]` with helper-driven collection while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Extended full call-order collection helper reuse in unit MCP client coverage:
  - added local unit-test helper `_unit_test_collect_full_call_order_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated initialize-cache full call-order collection comprehensions (including `session_id`) to helper-driven form in repeated-invoke/invalidate assertions while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - migrated force-reinitialize call-order pair collection to existing `_unit_test_collect_reentry_call_order_slice(...)` helper usage while preserving expected call-order vectors and trigger-path semantics unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Extended repeated collect+assert re-entry slice helper reuse in unit MCP client coverage:
  - added local unit-test helpers `_assert_unit_test_collected_primary_reentry_slice(...)` and `_assert_unit_test_collected_backup_reentry_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated patterns that collected re-entry slices and immediately asserted expected primary/backup vectors to helper-driven calls across retry-window/unreachable tests while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- Completed failure-script progression/setup/snapshot helper assertion vectorization in nearby cluster NAT helper validation coverage:
  - added local unit-test helpers `_assert_unit_test_failure_script_progression(...)`, `_set_unit_test_failure_script(...)`, `_set_unit_test_failure_scripts(...)`, `_assert_unit_test_failure_script_consumed_actions_in_order(...)`, `_assert_unit_test_failure_script_snapshot_after_consumed_actions(...)`, `_assert_unit_test_failure_script_snapshot_after_consumed_action(...)`, `_unit_test_failure_script_single_action_steps(...)`, `_unit_test_failure_script_reopen_setup_steps(...)`, and `_assert_unit_test_failure_script_snapshots_after_consumed_actions(...)`, plus local expected-action/setup vectors `UNIT_TEST_FAILURE_SCRIPT_ISOLATION_FINAL_ACTION_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_ISOLATION_SNAPSHOT_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_ISOLATION_SETUP_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_MIXED_FAILOVER_SETUP_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_PRIMARY_INITIALIZE_TIMEOUT_TIMEOUT_OK_SETUP_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_OK_TIMEOUT_ERROR_ACTION_VECTOR`, and `UNIT_TEST_FAILURE_SCRIPT_OK_ACTION_VECTOR` in `tests/unit/test_mcp_client.py`.
  - migrated repeated failure-script setup+consume progression assertions, repeated `set_failure_script(...)` setup blocks, repeated consumed-action ordering sequences, repeated consumed-action-plus-state-snapshot sequences, remaining repeated single-step/multi-step consumed-action wrapper assertions, remaining inline consumed-action tuples passed to progression helpers, remaining inline single-step action-tuple wrapper in snapshot assertions, repeated adjacent single-step snapshot assertions, nearby repeated multi-step setup sequences in validation tests, additional mixed-failover/reopen setup sequences, and repeated primary-initialize timeout-timeout-ok setup sequences to helper/constant-driven form while keeping server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved focused timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
## Active Next Slice (Recommended)
Continue `P12/P13` test-structure hardening by consolidating residual NAT helper expected vectors:
1. Reuse shared expected vectors in `tests/unit/test_mcp_client.py` where this improves consistency in nearby NAT helper tests:
   - migrate any remaining nearby repeated setup sequences used in failure-script helper setup/assertion paths into shared local setup-step vectors/helpers while keeping server-name setup literals and method-branch conditionals explicit.
   - keep server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
2. Preserve regression and semantics:
   - keep focused timeout-category constant regression coverage explicit and unchanged.
   - preserve invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
3. Keep scope and workflow tight:
   - scope edits to `tests/unit/test_mcp_client.py` only (no product code changes).
   - run full validation and update both plan docs after completion.

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
5. Refresh handoff snapshot metadata:
   - `./scripts/update_handoff_snapshot.sh --pytest-passed <N>`
6. Record new state back into this file and `todo/master_plan.md`.

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
