# P11 - tool_orchestrator

## Status
in_progress

## Phase
0.4

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
- Implemented orchestrated change workflow in `src/att/core/tool_orchestrator.py`.
- Workflow now emits and persists `code.changed`, `test.run`, `test.passed`/`test.failed`, and optional `git.commit` events.
- Added workflow API route: `POST /api/v1/projects/{project_id}/workflows/change-test`.
- Added event query API route: `GET /api/v1/projects/{project_id}/events` with optional event-type filter.
- Added unit coverage in `tests/unit/test_tool_orchestrator.py` and integration coverage in `tests/integration/test_api_workflows_events.py`.
