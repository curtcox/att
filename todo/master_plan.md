# ATT (Agent Toolkit Toolkit) Master Plan

## Vision

ATT is a web-based application for developing, running, debugging, and deploying NVIDIA NeMo Agent Toolkit (NAT) apps. It is built on NAT itself, exposes an OpenAPI interface, and functions as both an MCP client and MCP server. The top priority is reaching self-bootstrapping: the point where ATT can create future versions of itself.

## Implementation Progress (2026-02-14)

- See done for older completed implementation details:
  - `/Users/curt/me/att/done/master_plan_implementation_progress_archive_2026-02-13.md`

- [x] Completed failure-script setup/ordering/snapshot helper vectorization in nearby cluster NAT helper coverage:
  - added local unit-test helpers `_set_unit_test_failure_script(...)`, `_set_unit_test_failure_scripts(...)`, `_set_unit_test_primary_failure_script(...)`, `_set_unit_test_primary_initialize_failure_script(...)`, `_set_unit_test_primary_initialize_timeout_timeout_ok_failure_script(...)`, `_set_unit_test_primary_timeout_ok_failure_script(...)`, `_set_unit_test_primary_ok_failure_script(...)`, `_set_unit_test_primary_initialize_timeout_failure_script(...)`, `_assert_unit_test_failure_script_consumed_actions_in_order(...)`, `_assert_unit_test_failure_script_snapshot_after_consumed_actions(...)`, `_assert_unit_test_failure_script_snapshot_after_consumed_action(...)`, `_unit_test_failure_script_single_action_steps(...)`, `_unit_test_failure_script_reopen_setup_steps(...)`, `_unit_test_primary_setup_steps(...)`, and `_assert_unit_test_failure_script_snapshots_after_consumed_actions(...)`, plus local expected-action/setup vectors `UNIT_TEST_FAILURE_SCRIPT_ISOLATION_FINAL_ACTION_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_ISOLATION_SNAPSHOT_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_ISOLATION_SETUP_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_MIXED_FAILOVER_SETUP_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_PRIMARY_INITIALIZE_TIMEOUT_TIMEOUT_OK_SETUP_STEPS`, `UNIT_TEST_FAILURE_SCRIPT_OK_TIMEOUT_ERROR_ACTION_VECTOR`, and `UNIT_TEST_FAILURE_SCRIPT_OK_ACTION_VECTOR` in `tests/unit/test_mcp_client.py`.
  - migrated repeated `set_failure_script(...)` setup blocks in nearby retry-window/reopen call-order tests, repeated consumed-action ordering assertions, repeated consumed-action-plus-state-snapshot sequences, remaining repeated single-step/multi-step consumed-action wrapper assertions, remaining inline consumed-action tuples passed to progression helpers, remaining inline single-step action-tuple wrapper in snapshot assertions, repeated adjacent single-step snapshot assertions, nearby repeated multi-step setup sequences in validation tests, additional mixed-failover/reopen setup sequences, repeated primary-initialize timeout-timeout-ok setup sequences, repeated primary timeout-ok setup sequences used by retry-window/resource-retry tests, repeated primary ok setup sequences in exhaustion method-branch setup paths, repeated primary initialize timeout-timeout-ok setup invocation sequences in nearby unreachable-primary tests, repeated primary timeout-ok/ok setup invocation sequences in nearby retry-window and exhaustion method-branch paths, single-step primary invalid-vector setup invocation in failure-script order validation, and primary initialize + timeout-timeout-ok/timeout-ok/ok/setup-routing invocation plumbing via shared primary setter + initialize wrapper helpers (including setup-step constant reuse in the timeout-timeout-ok wrapper, initialize-timeout primary_failures==1 branch routing through the initialize wrapper, and nearby unreachable-primary setup routing through the initialize-timeout helper with explicit failure count) to helper/constant-driven form while keeping server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved focused timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed adapter-session freshness diagnostics helper reuse in non-matrix parity paths:
  - added local unit-test helper `_assert_unit_test_server_diagnostics_freshness(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated adapter-session freshness retrieval + assertion scaffolding (`adapter_session_diagnostics(...)` + non-`None` + freshness assertion) in freshness semantics checks to helper-driven form while keeping server-name setup literals and method semantics explicit and unchanged.
  - preserved focused timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed adapter-session diagnostics retrieval helper reuse in non-matrix parity paths:
  - added local unit-test helper `_unit_test_server_diagnostics(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated adapter-session diagnostics retrieval + non-`None` scaffolding in nearby adapter-session control/disconnect tests to helper-driven form while keeping server-name setup literals and method semantics explicit and unchanged.
  - preserved focused timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed repeated-invokes expected progression constant reuse in NAT cluster unit coverage:
  - added local unit-test constant `UNIT_TEST_CLUSTER_NAT_REPEATED_INVOKES_PROGRESSIONS` in `tests/unit/test_mcp_client.py`.
  - migrated inline expected call-method progression vectors in `test_cluster_nat_repeated_invokes_skip_initialize_until_invalidate` to constant-driven form.
  - kept server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed force-reinitialize expected re-entry call-order vector constant reuse in NAT cluster parity coverage:
  - added local unit-test constant `UNIT_TEST_CLUSTER_NAT_FORCE_REINITIALIZE_REENTRY_CALL_ORDER_LISTS` in `tests/unit/test_mcp_client.py`.
  - migrated inline expected re-entry call-order list materialization in `test_cluster_nat_force_reinitialize_triggers_call_order_parity` to constant-driven form.
  - kept server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed residual primary resource re-entry expected-vector constant reuse in NAT helper coverage:
  - added local unit-test constant `UNIT_TEST_PRIMARY_RESOURCE_REENTRY_CALL_ORDER_SLICE` in `tests/unit/test_mcp_client.py`.
  - migrated remaining inline re-entry call-order list assertion in `test_cluster_nat_resource_retry_reentry_skips_non_retryable_backup_state` to constant-driven form.
  - kept server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed reopen initialize-start server-order expected-vector constant reuse in NAT helper coverage:
  - added local unit-test constant `UNIT_TEST_CLUSTER_NAT_REOPEN_INITIALIZE_START_SERVER_ORDERS` in `tests/unit/test_mcp_client.py`.
  - migrated inline expected initialize-start server order assertion in `test_cluster_nat_simultaneous_unreachable_reopen_prefers_ordered_candidates` to constant-driven form.
  - kept server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed timeout-script action vector constant reuse in nearby cluster NAT helper coverage:
  - added local unit-test constants `UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_VECTOR`, `UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_OK_VECTOR`, and `UNIT_TEST_FAILURE_SCRIPT_TIMEOUT_TIMEOUT_OK_VECTOR` in `tests/unit/test_mcp_client.py`.
  - migrated remaining inline timeout-script setup vectors in nearby cluster NAT helper tests to constant-driven form (mixed scripted failover, retry-window re-entry, resource retry re-entry, unreachable/reopen paths, and failure-script isolation).
  - kept server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed non-timeout failure-script action vector constant reuse in nearby cluster NAT helper coverage:
  - added local unit-test constant `UNIT_TEST_FAILURE_SCRIPT_ERROR_OK_VECTOR` in `tests/unit/test_mcp_client.py`.
  - migrated remaining inline non-timeout failure-script setup vectors (`"ok"`, `"error"`, and `"error"+"ok"`) in nearby cluster NAT helper tests to constant-driven form.
  - kept server-name setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed failure-script state-check helper assertion reuse in nearby cluster NAT helper validation coverage:
  - added local unit-test helper `_assert_unit_test_failure_script_state_snapshot(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated failure-script state-check assertion blocks in `test_cluster_nat_failure_script_isolation_across_servers_and_methods` to helper-driven form while keeping setup literals and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed terminal failure-script consume-state helper assertion reuse in nearby cluster NAT helper validation coverage:
  - added local unit-test helper `_assert_unit_test_failure_script_terminal_state(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated post-exhaustion consume-state assertions (`is None`) in `test_cluster_nat_failure_script_isolation_across_servers_and_methods` to helper-driven form while keeping setup literals and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed single-method failure-script consume-state helper assertion reuse in nearby cluster NAT helper validation coverage:
  - added local unit-test helper `_assert_unit_test_failure_script_method_exhausted(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated single-method post-exhaustion consume-state assertions in `test_cluster_nat_failure_script_order_and_validation` to helper-driven form while keeping setup literals and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed non-terminal failure-script consume-action helper assertion reuse in nearby cluster NAT helper validation coverage:
  - added local unit-test helper `_assert_unit_test_failure_script_consumed_action(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated non-terminal consume-action assertions in `test_cluster_nat_failure_script_order_and_validation` and `test_cluster_nat_failure_script_isolation_across_servers_and_methods` to helper-driven form while keeping setup literals and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Completed NAT transport failure/category matrix constant reuse in unit adapter parity coverage:
  - added local unit-test constant `UNIT_TEST_NAT_CATEGORY_MAPPING_FAILURE_MATRIX` in `tests/unit/test_mcp_client.py`.
  - migrated the inline `("failure", "category")` parametrize matrix in `test_nat_transport_adapter_category_mapping_parity` to constant-driven form.
  - kept server-name setup literals and transport payload literals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Completed residual invoke/failover transport error literal cleanup in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_ERROR_CONNECT_TIMEOUT` and `UNIT_TEST_ERROR_PRIMARY_UNAVAILABLE`.
  - migrated repeated invoke/failover transport exception message literals (`"connect timeout"` and `"primary unavailable"`) to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category constant regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Completed residual manual-degrade health error literal cleanup in unit MCP client coverage:
  - added local unit-test constant `UNIT_TEST_ERROR_MANUAL_DEGRADE`.
  - migrated the remaining inline `record_check_result(..., error="manual degrade")` path in `tests/unit/test_mcp_client.py` to constant-driven form.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended health-check error-message constant reuse in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_ERROR_DOWN`, `UNIT_TEST_ERROR_SLOW`, `UNIT_TEST_ERROR_HOLD_BACKUP`, and `UNIT_TEST_ERROR_HOLD_PRIMARY`.
  - migrated repeated `record_check_result(..., error=...)` text literals plus the scripted transport helper `return False, "down"` path to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended call-vector label constant reuse in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_SESSION_CALL_ENTRY_LABEL` and `UNIT_TEST_RESOURCE_CALL_ENTRY_LABEL`.
  - migrated remaining inline tuple-label literals (`"session"` and `"resource"`) in session-call assertion vectors to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended full projects-URI constant reuse across resource paths in unit MCP client coverage:
  - migrated remaining inline `"att://projects"` literals in transport payload setup/assertions and resource-helper paths to `UNIT_TEST_PROJECTS_URI` in `tests/unit/test_mcp_client.py` (the literal now appears only in constant definition).
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended full project-list tool-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `"att.project.list"` literals in transport payload setup/assertions and invoke-call arguments to `UNIT_TEST_PROJECT_LIST_TOOL_NAME` in `tests/unit/test_mcp_client.py` (the literal now appears only in constant definition).
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended tool-name constant reuse for invoke paths in unit MCP client coverage:
  - added local unit-test constant `UNIT_TEST_PROJECT_LIST_TOOL_NAME` and migrated repeated inline `invoke_tool("att.project.list", ...)` call arguments to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended resource-URI constant reuse in unit MCP client coverage:
  - migrated remaining inline `read_resource("att://projects", ...)` call arguments to `read_resource(UNIT_TEST_PROJECTS_URI, ...)` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended full `should_retry(...)` terminal server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `should_retry("terminal", now=...)` call arguments to `should_retry(UNIT_TEST_TERMINAL_SERVER, now=...)` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended `should_retry(...)` server-name constant reuse in unit MCP client coverage:
  - migrated inline `should_retry("terminal")` call arguments to `should_retry(UNIT_TEST_TERMINAL_SERVER)` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended final `record_check_result(...)` server-name constant reuse in unit MCP client coverage:
  - added local unit-test constant `UNIT_TEST_TERMINAL_SERVER` and migrated the remaining inline `record_check_result("terminal", ...)` call arguments to constant-driven form in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended `record_check_result(...)` server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `record_check_result(...)` server-name arguments with existing constants (`"primary"`, `"backup"`, `"degraded"`, `"github"`, `"a"`, `"b"`) to `UNIT_TEST_*` constants in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended remaining state-inspection server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `manager.get("primary")`, `manager.get("backup")`, and `manager.get("recovered")` call arguments to `UNIT_TEST_PRIMARY_SERVER`, `UNIT_TEST_BACKUP_SERVER`, and `UNIT_TEST_RECOVERED_SERVER` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended state-inspection accessor server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `manager.get("codex")` and `manager.get("github")` call arguments to `UNIT_TEST_CODEX_SERVER` and `UNIT_TEST_GITHUB_SERVER` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended initialize/list-filter server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `initialize_server("codex")`, `initialize_server("github")`, and `list_adapter_sessions(server_name="c")` call arguments to constants (`UNIT_TEST_CODEX_SERVER`, new `UNIT_TEST_GITHUB_SERVER`, and `UNIT_TEST_SERVER_C`) in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended adapter-scoped helper server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `adapter.session_diagnostics("nat")`, `adapter.invalidate_session("nat")`, and `list_adapter_sessions(server_name="nat")` call arguments to `UNIT_TEST_NAT_SERVER` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended adapter control server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `adapter_session_diagnostics("nat")`, `initialize_server("nat")`, `refresh_adapter_session("nat")`, and adjacent `get("nat")` call arguments to `UNIT_TEST_NAT_SERVER` in `tests/unit/test_mcp_client.py`.
  - kept registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Extended adapter invalidation server-name constant reuse in unit MCP client coverage:
  - migrated remaining inline `invalidate_adapter_session("nat")` and `invalidate_adapter_session("primary")` call arguments to existing constants (`UNIT_TEST_NAT_SERVER`, `UNIT_TEST_PRIMARY_SERVER`) in `tests/unit/test_mcp_client.py`.
  - preserved registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

- [x] Standardized snapshot-refresh process trigger and shortcut:
  - updated `/Users/curt/me/att/AGENTS.md` to require handoff snapshot refresh after validation using `./scripts/update_handoff_snapshot.sh --pytest-passed <N>` (or shortcut form).
  - added `/Users/curt/me/att/Makefile` with `make snapshot PASSED=<pytest_pass_count>` shortcut that invokes the updater script.
  - preserves product/runtime behavior unchanged while making process-trial adoption repeatable and explicit.

- [x] Added process-change proposal doc and started two concrete trials:
  - added `/Users/curt/me/att/todo/proposed_process_changes.md` capturing the six proposed process changes and marking trial picks.
  - trial 1: added `/Users/curt/me/att/scripts/update_handoff_snapshot.sh` to auto-update handoff snapshot fields (`Date`, `Branch`, `HEAD`, `Last commit`, working-tree state) plus optional pytest pass count (`--pytest-passed`).
  - trial 2: extended `/Users/curt/me/att/tests/unit/test_docs_guardrails.py` with `test_master_plan_size_guardrail` and `MAX_MASTER_PLAN_LINES = 1300`, complementing the existing handoff-size guardrail.
  - preserved product/runtime behavior unchanged while adding CI-visible planning-file guardrails and a repeatable snapshot-maintenance utility.

- [x] Added automated handoff-size guardrail test coverage:
  - added new unit test `/Users/curt/me/att/tests/unit/test_docs_guardrails.py` with `test_next_machine_handoff_size_guardrail`.
  - guardrail enforces `todo/NEXT_MACHINE_HANDOFF.md` max size of `250` lines and fails with explicit archive guidance (`done/`) when exceeded.
  - preserves runtime/product behavior unchanged while adding CI-visible alerting for handoff growth.

- [x] Extended invocation-filter server-name constant reuse in unit MCP client coverage:
  - migrated the remaining diagnostics filter argument literal `list_invocation_events(server="primary", ...)` to `UNIT_TEST_PRIMARY_SERVER` in `tests/unit/test_mcp_client.py`.
  - preserved diagnostics filter scope (`server`, `method`, `request_id`), request sequencing, timeout-toggle setup flow, and method-branch conditionals unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended timeout-toggle server-name constant reuse in unit MCP client coverage:
  - migrated remaining timeout-toggle setup literals `factory.fail_on_timeout_initialize.add("primary")`, `factory.fail_on_timeout_tool_calls.add("primary")`, and `factory.fail_on_timeout_resource_reads.add("primary")` to `UNIT_TEST_PRIMARY_SERVER` in `tests/unit/test_mcp_client.py`.
  - preserved timeout-toggle setup flow, failure-script vectors, preferred-order inputs, and method-branch conditionals unchanged while reducing setup-side server literal duplication.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended `set_failure_script` server-name constant reuse in unit MCP client coverage:
  - migrated the remaining inline `set_failure_script("primary", method, ...)` setup wiring in retry-window resource re-entry coverage to `UNIT_TEST_PRIMARY_SERVER`.
  - preserved failure-script action vectors, preferred-order inputs, setup sequencing, and method-branch conditionals unchanged while reducing setup-side server literal duplication.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended `set_failure_script` method constant reuse in unit MCP client coverage:
  - migrated remaining inline `set_failure_script(..., "initialize" | "tools/call" | "resources/read", ...)` setup literals in `tests/unit/test_mcp_client.py` to existing method constants (`UNIT_TEST_INITIALIZE_METHOD`, `UNIT_TEST_TOOLS_CALL_METHOD`, `UNIT_TEST_RESOURCES_READ_METHOD`).
  - preserved failure-script action vectors, preferred-order inputs, setup sequencing, and method-branch conditionals unchanged while reducing setup-side method literal duplication.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended mixed-method call-order collection helper reuse in unit MCP client coverage:
  - added local unit-test helper `_unit_test_collect_mixed_method_call_order_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated the remaining inline mixed-method call-order collection comprehension (`initialize` + `tools/call` + `resources/read`) in scripted failover call-order assertions to helper-driven form while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended method-scoped re-entry pair collection helper reuse in unit MCP client coverage:
  - migrated remaining inline resource retry re-entry call-order pair collection in `tests/unit/test_mcp_client.py` to `_unit_test_collect_reentry_call_order_slice(...)`.
  - replaced repeated list-comprehension scaffolding `[(server, method) for ... if method in {UNIT_TEST_INITIALIZE_METHOD, UNIT_TEST_RESOURCES_READ_METHOD}]` with helper-driven collection while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended full call-order collection helper reuse in unit MCP client coverage:
  - added local unit-test helper `_unit_test_collect_full_call_order_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated initialize-cache full call-order collection comprehensions (including `session_id`) to helper-driven form in repeated-invoke/invalidate assertions while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - migrated force-reinitialize call-order pair collection to existing `_unit_test_collect_reentry_call_order_slice(...)` helper usage while preserving expected call-order vectors and trigger-path semantics unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended collected reopen-slice expected-vector helper reuse in unit MCP client coverage:
  - added local unit-test helper `_assert_unit_test_reopen_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated the remaining explicit simultaneous-unreachable reopen-slice expectation assertion to helper-driven form while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended repeated collect+assert re-entry slice helper reuse in unit MCP client coverage:
  - added local unit-test helpers `_assert_unit_test_collected_primary_reentry_slice(...)` and `_assert_unit_test_collected_backup_reentry_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated patterns that collected re-entry slices and immediately asserted expected primary/backup vectors to helper-driven calls across retry-window/unreachable tests while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended repeated re-entry slice collection helper reuse in unit MCP client coverage:
  - added local unit-test helper `_unit_test_collect_reentry_call_order_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated list-comprehension scaffolding that collected `initialize`+`method` re-entry slices from `factory.calls[start:]` to helper-driven collection across retry-window/unreachable and simultaneous-reopen call-order assertions while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended repeated re-entry slice assertion helper reuse in unit MCP client coverage:
  - added local unit-test assertion helpers `_assert_unit_test_primary_reentry_slice(...)` and `_assert_unit_test_backup_reentry_slice(...)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated assertion-side re-entry slice checks (`assert <slice_var> == _unit_test_*_reentry_call_order_slice(method)`) to helper-driven assertions across retry-window/unreachable tests while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended repeated two-entry re-entry call-order slice helper reuse in unit MCP client coverage:
  - added local unit-test helpers `_unit_test_primary_reentry_call_order_slice(method)` and `_unit_test_backup_reentry_call_order_slice(method)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated assertion-side two-entry re-entry vectors to helper-driven assertions across retry-window/unreachable call-order checks while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended dynamic call-order tuple helper reuse in unit MCP client coverage:
  - added local unit-test helpers `_unit_test_primary_method_call_order_entry(method)` and `_unit_test_backup_method_call_order_entry(method)` in `tests/unit/test_mcp_client.py`.
  - migrated repeated assertion-side dynamic tuple literals `(UNIT_TEST_PRIMARY_SERVER, method)` and `(UNIT_TEST_BACKUP_SERVER, method)` across retry-window/unreachable call-order assertions to helper-driven tuple construction while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended repeated call-order initialize tuple constant reuse in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_PRIMARY_INITIALIZE_CALL_ORDER_ENTRY` and `UNIT_TEST_BACKUP_INITIALIZE_CALL_ORDER_ENTRY` in `tests/unit/test_mcp_client.py`.
  - migrated repeated assertion-side call-order slice initialize tuples in retry-window/unreachable re-entry assertions to shared constants while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended repeated server-name list assertion vector constant reuse in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_SERVER_A_B_VECTOR` and `UNIT_TEST_SERVER_C_VECTOR` in `tests/unit/test_mcp_client.py`.
  - migrated repeated assertion-side server-name list expectations (`[UNIT_TEST_SERVER_A, UNIT_TEST_SERVER_B]` and `[UNIT_TEST_SERVER_C]`) to shared vectors across initialize-all and adapter session diagnostics assertions while keeping registration/setup literals, preferred-order inputs, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended repeated phase-list assertion vector constant reuse in unit MCP client coverage:
  - added local unit-test constants `UNIT_TEST_INITIALIZE_START_FAILURE_PHASES` and `UNIT_TEST_INVOKE_START_SUCCESS_PHASES` in `tests/unit/test_mcp_client.py`.
  - migrated repeated assertion-side phase-list expectations (`[UNIT_TEST_INITIALIZE_START_PHASE, UNIT_TEST_INITIALIZE_FAILURE_PHASE]` and `[UNIT_TEST_INVOKE_START_PHASE, UNIT_TEST_INVOKE_SUCCESS_PHASE]`) to shared constants in timeout-phase and invocation-event filter assertions while keeping registration/setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended capability snapshot `server_info` assertion dictionary constant reuse in unit MCP client coverage:
  - added local unit-test constant `UNIT_TEST_GITHUB_SERVER_INFO` in `tests/unit/test_mcp_client.py`.
  - migrated repeated assertion-side comparisons against `{"name": "github", "version": "2.0.0"}` for `capability_snapshot.server_info` to the shared constant while keeping registration/setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.
- [x] Extended remaining order-test failure-action timeout/error assertion constant reuse in unit MCP client coverage:
  - added local unit-test constant `UNIT_TEST_FAILURE_ACTION_TIMEOUT` in `tests/unit/test_mcp_client.py`.
  - migrated remaining order-test and adjacent scripted isolation `consume_failure_action(... ) == "timeout"` assertions to `UNIT_TEST_FAILURE_ACTION_TIMEOUT` and migrated the remaining order-test `== "error"` assertion to existing `UNIT_TEST_FAILURE_ACTION_ERROR`, while keeping `set_failure_script(...)` setup inputs, registration/setup literals, transport payload literals, and method-branch conditionals explicit and unchanged.
  - preserved timeout-category regression semantics plus invocation-event/connection-event filters and call-order/subsequence behavior unchanged.

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
