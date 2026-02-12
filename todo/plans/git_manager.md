# P06 - git_manager

## Status
in_progress

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
- Implemented baseline git operations (`status`, `add/commit`, `push`, `branch`, `log`) in `src/att/core/git_manager.py`.
- Added GitHub CLI-backed operations for Actions and PR lifecycle:
  - `actions`
  - `pr_create`
  - `pr_merge`
  - `pr_reviews`
- Wired API routes under `src/att/api/routes/git.py` to these operations.
- Added integration coverage updates in `tests/integration/test_api_feature_endpoints.py`.
- `GitManager` operations are now consumed by self-bootstrap adapters for CI/PR lifecycle hooks.
