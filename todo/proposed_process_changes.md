# Proposed Process Changes

## Candidate Changes

1. Batch micro-refactors into one slice
- Run 3 to 5 related constant/helper cleanups per slice before full validation, instead of one tiny change at a time.

2. Add a handoff snapshot updater script
- Create `scripts/update_handoff_snapshot.sh` to auto-fill HEAD, last commit, working-tree state, and latest validation count in `todo/NEXT_MACHINE_HANDOFF.md`.

3. Reduce commit noise
- Use one commit per slice that includes both code and plan-doc updates, and only do a separate snapshot commit when truly needed.

4. Add a second doc guardrail
- Add a test for `todo/master_plan.md` growth, similar to the handoff-size test, so both active planning docs stay bounded.

5. Define a fixed archive policy
- Document a simple rule like “keep last N items in active docs, archive older to `done/` weekly” to avoid manual decisions each time.

6. Prioritize behavior-impact slices more often
- Mix in slices that improve test quality, failure messages, or coverage relevance, not only literal/constant normalization, so each cycle has clearer value.

## Trials To Run Now

1. Trial `#2`: handoff snapshot updater script.
2. Trial `#4`: second doc guardrail for `todo/master_plan.md`.
