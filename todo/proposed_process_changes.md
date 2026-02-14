# Proposed Process Changes

## Bottom-Line Decisions

### Adopt Now

1. Candidate `#2`: handoff snapshot updater script.
   - Status: **adopted**.
   - Evidence: `scripts/update_handoff_snapshot.sh` is implemented and in active use.

2. Candidate `#4`: second doc guardrail.
   - Status: **adopted**.
   - Evidence: `tests/unit/test_docs_guardrails.py` enforces limits for both
     `todo/NEXT_MACHINE_HANDOFF.md` and `todo/master_plan.md`.

### Continue as Policy

3. Candidate `#6`: prioritize behavior-impact slices more often.
   - Status: **policy (ongoing)**.
   - Intent: keep mixing behavior-impact slices (test quality/failure clarity/coverage relevance)
     alongside structural cleanup slices.

### Trial Next

4. Candidate `#3`: reduce commit noise.
   - Status: **queued trial**.
   - Trial rule: target one commit per slice including code + plan docs,
     and only split snapshot into a second commit when necessary.
   - Success metric: >= 80% of slices over next 10 slices end as one commit.

5. Candidate `#1`: batch micro-refactors into one slice.
   - Status: **queued trial**.
   - Trial rule: batch 2 to 3 tightly related cleanups per slice (not 5 initially).
   - Success metric: lower per-slice overhead without increased rollback/rework.

6. Candidate `#5`: fixed archive policy.
   - Status: **queued trial**.
   - Trial rule: archive weekly, keep only last N completed bullets in active docs.
   - Success metric: no ad hoc archive debates during daily slices.

## New Candidate Trials

1. Single-commit slice enforcement.
   - Trial rule: one commit per slice by default.
   - Success metric: >= 80% one-commit slices over next 10 slices.

2. Validation tiering for tiny test-only refactors.
   - Trial rule: use targeted checks for small doc/test-only slices; run full suite every N slices
     and before handoff.
   - Success metric: reduced cycle time with no rise in post-merge regressions.

3. Refactor completion criteria.
   - Trial rule: define explicit "done" criteria for the current helper-normalization campaign.
   - Success metric: campaign closes predictably rather than drifting into endless micro-slices.
