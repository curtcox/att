# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (uncommitted runtime + self-bootstrap hardening increments)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`125 passed`)

## Recent Delivered Work
- Runtime health + log streaming delivery complete for current slice:
  - `RuntimeManager.probe_health()` and status diagnostics
  - cursor-based runtime log reads (`read_logs`, API logs cursor/limit, MCP tool/resource cursor/limit)
- Self-bootstrap rollback hardening delivered:
  - release-aware request/result metadata (`requested_release_id`, `previous_release_id`, `rollback_release_id`, `deployed_release_id`, `rollback_target_release_id`)
  - release metadata source integration via provider hook + default git source (`HEAD`, `HEAD^`), surfaced as `release_metadata_source`
  - rollback policy gate before executor call, with explicit outcomes:
    - `rollback_policy_status`
    - `rollback_policy_reason`
    - `rollback_target_valid`
  - deny-before-execute path implemented (e.g. rollback target == deployed release)
  - policy-denial events recorded with `phase="rollback_policy"`
- API schema/route updates wired for new self-bootstrap output fields.
- Test coverage expanded for policy allow/deny and release-metadata-provider flows.

## Active Next Slice (Recommended)
Focus next on `P16` production policy hardening with stronger source-of-truth integration:
1. Add release-source adapter abstraction beyond git commit history.
2. Enforce rollback policy matrix by failure class and deployment context.

Suggested implementation direction:
- Introduce a release source adapter contract (e.g. deployment registry / runtime manager signal) and fallback chain.
- Add failure classification in self-bootstrap (`deploy_failure`, `watchdog_failure`, `health_failure`) and map each class to policy outcomes.
- Add explicit policy override controls in request model for controlled operations.
- Extend unit/integration tests for adapter fallbacks and policy matrix branches.

## Resume Checklist
1. Sync and verify environment:
   - `git pull`
   - `./.venv313/bin/python --version`
2. Read context docs:
   - `todo/master_plan.md`
   - `todo/plans/runtime_manager.md`
   - `todo/plans/self_bootstrap.md`
3. Implement one slice end-to-end (code + tests + plan updates).
4. Run validation:
   - `./.venv313/bin/ruff format .`
   - `./.venv313/bin/ruff check .`
   - `PYTHONPATH=src ./.venv313/bin/mypy`
   - `PYTHONPATH=src ./.venv313/bin/pytest`
5. Record new state back into this file and `todo/master_plan.md`.

## Key Files for Next Slice
- `src/att/core/self_bootstrap_manager.py`
- `src/att/api/deps.py`
- `src/att/api/routes/self_bootstrap.py`
- `src/att/api/schemas/self_bootstrap.py`
- `tests/unit/test_self_bootstrap_manager.py`
- `tests/integration/test_api_self_bootstrap.py`

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (runtime health/log stream + release-aware rollback metadata/policy gates done; remaining work is production release-source and policy-matrix hardening).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
