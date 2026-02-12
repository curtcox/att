# P08 - test_runner

## Status
in_progress

## Phase
0.4

## Dependencies
P03,P05

## Scope
- Define concrete implementation tasks.
- Define required tests and acceptance criteria.
- Track delivery notes and unresolved risks.

## Acceptance Criteria
- The implementation is merged with passing CI checks.
- Tests for this plan item exist and cover baseline behavior.
- `todo/master_plan.md` is updated with completion status.

## Notes
- Expanded `TestRunner.run` in `src/att/core/test_runner.py` with:
  - suite alias mapping plus support for direct pytest target paths (`tests/...` or `...::test_name`)
  - optional marker filtering (`-m ...`)
  - optional subprocess timeout handling with deterministic timeout return (`returncode=124`, `timed_out=True`)
- Added parsed pytest summary metadata to `RunResult`:
  - `passed`, `failed`, `skipped`, `errors`, `xfailed`, `xpassed`
  - `duration_seconds`
  - `no_tests_collected`
- Added parser helpers:
  - `parse_pytest_output_summary`
  - `parse_pytest_json_report`
  - `parse_pytest_junit_xml`
- Added transport payload helper `RunResult.as_payload()` and wired enriched test results through:
  - `POST /api/v1/projects/{project_id}/test/run`
  - `GET /api/v1/projects/{project_id}/test/results`
  - MCP `att.test.run` / `att.test.results` handlers in transport
- Expanded MCP test-tool adapter in `src/att/mcp/tools/test_tools.py` with optional `markers` and `timeout_seconds`.
- Added coverage in:
  - `tests/unit/test_test_runner.py`
  - `tests/unit/test_test_tools.py`
  - existing integration coverage in `tests/integration/test_api_feature_endpoints.py`
- Remaining scope before completion:
  - Structured failure detail extraction (per-test traces) in API/MCP payloads.
  - Coverage threshold enforcement/report parsing integration.
