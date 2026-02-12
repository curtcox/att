# P04 - project_manager

## Status
completed

## Phase
0.4

## Dependencies
P03

## Scope
- Define concrete implementation tasks.
- Define required tests and acceptance criteria.
- Track delivery notes and unresolved risks.

## Acceptance Criteria
- The implementation is merged with passing CI checks.
- Tests for this plan item exist and cover baseline behavior.
- `todo/master_plan.md` is updated with completion status.

## Notes
- Implemented baseline project lifecycle methods: `create`, `list`, `get`, and `delete`.
- Added clone support via async git CLI execution in `src/att/core/project_manager.py::clone`.
- Added archive download support in `src/att/core/project_manager.py::download` (zip artifact generation).
- Exposed clone/download APIs in `src/att/api/routes/projects.py`:
  - `POST /api/v1/projects/clone`
  - `GET /api/v1/projects/{project_id}/download`
- Added coverage in:
  - `tests/unit/test_project_manager.py`
  - `tests/integration/test_api_projects.py`
