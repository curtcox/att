# Repository Agent Instructions

## Startup
1. Read `todo/NEXT_MACHINE_HANDOFF.md` before making changes.
2. Follow the "Active Next Slice" and "Resume Checklist" sections in that file.
3. Update both `todo/NEXT_MACHINE_HANDOFF.md` and `todo/master_plan.md` as progress is made.

## Continuity Rule
- If the user says "Continue", resume from `todo/NEXT_MACHINE_HANDOFF.md` without re-planning from scratch.

# Development Process
Use TDD for new features and bug fixes.
Red, green, refactor.
Commit often.
After validation passes, refresh `todo/NEXT_MACHINE_HANDOFF.md` snapshot metadata via
`./scripts/update_handoff_snapshot.sh --pytest-passed <N>` (or `make snapshot PASSED=<N>`).

When I report a bug, don't start by trying to fix it.
Instead, start by writing a test that reproduces the bug.
Then, try to fix the bug and prove it with a passing test.
