# Repository Agent Instructions

## Startup
1. Read `todo/NEXT_MACHINE_HANDOFF.md` before making changes.
2. Follow the "Active Next Slice" and "Resume Checklist" sections in that file.
3. Update both `todo/NEXT_MACHINE_HANDOFF.md` and `todo/master_plan.md` as progress is made.

## Handoff Productivity
- Prefer `./.venv/bin/python scripts/handoff_helper.py quickview --file todo/NEXT_MACHINE_HANDOFF.md` (or `make handoff-quickview`) when you need a fast context refresh.
- Prefer `./.venv/bin/python scripts/handoff_helper.py prepend-recent ...` (or `make handoff-prepend SUMMARY="..."`) when adding new `Recent Delivered Work` bullets.
- Continue using `./scripts/update_handoff_snapshot.sh --pytest-passed <N>` (or `make snapshot PASSED=<N>`) after validation.

## Process Trials Alignment
- Keep execution aligned with `todo/proposed_process_changes.md` statuses (`adopted`, `policy`, `queued trial`).
- Re-evaluate queued process trials every Friday and record decisions in `todo/proposed_process_changes.md`.

## Continuity Rule
- If the user says "Continue", resume from `todo/NEXT_MACHINE_HANDOFF.md` without re-planning from scratch.

## Autopilot working agreement
- Execute the plan end-to-end; do NOT wait for me to say “Continue”.
- Only stop when you truly need a human decision (ambiguity, tradeoff choice, missing credential, failing test you can’t resolve).
- When you must stop, ask exactly ONE question and prefix it with: NEEDS_INPUT:
- After each meaningful chunk of work:
  - run the relevant tests/lint
  - ensure `git status` is clean
  - commit with a descriptive message
  - push to origin (no force-push)

# Development Process
Use TDD for new features and bug fixes.
Red, green, refactor.
Commit often.
After validation passes, refresh `todo/NEXT_MACHINE_HANDOFF.md` snapshot metadata via
`./scripts/update_handoff_snapshot.sh --pytest-passed <N>` (or `make snapshot PASSED=<N>`).

When I report a bug, don't start by trying to fix it.
Instead, start by writing a test that reproduces the bug.
Then, try to fix the bug and prove it with a passing test.

## Default workflow: strict TDD (red → green → refactor)

When implementing, fixing, or refactoring **production code** in this repository:

- **Follow the `tdd` skill as the governing procedure.**
  - If skills are available, prefer invoking it (`@tdd` in Windsurf / `$tdd` in Codex) when doing code changes.
  - If multiple skills apply, `tdd` takes precedence for any task that changes runtime behavior.
- Work in **vertical slices**: one failing test → minimal code to pass → repeat.
- Prefer **integration-style tests** through **public interfaces**; avoid mocking internals unless strictly necessary at boundaries.
- Do **not** refactor while tests are failing; get back to green first.
- Run the relevant tests after each small step; stop immediately on failures and fix before continuing.
