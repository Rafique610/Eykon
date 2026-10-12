# Phase 8 Step 03 — Final System Runs on Held-Out v3, Both Phones

## What

Run the frozen system once on the v3 data, exactly as the protocol says:

- **Pipelines**: cascade (and path C / V per configuration), memory build,
  conversation processing, for each configuration L0–L3 and the product
  default.
- **Questions**: every v3 question through every configuration (laptop runner
  from Phase 5.2 Step 09), plus a fixed subset on both phones end to end
  (Phase 5.2 Step 14 method).
- **Phone runs**: the v3 objects sessions replayed on both phones with the
  live pipeline (Phase 6 replay mode) for cost numbers; one v3 meeting
  processed on both phones.
- **Outputs**: answers, scores (automatic part), costs, all with manifests.

## Why

- These are the numbers in the thesis's main results chapter. One run, frozen
  system, unseen data.

## How to implement

1. Scripts from earlier phases, pointed at `split: final_v3`; no new logic.
2. A run log with start / end times, hashes, any failures (a failure is
   recorded, fixed only if it is a bug in running, not in behaviour, and the
   rerun is logged).
3. Automatic scoring immediately; human scoring in Step 05.

## Open decisions

- **Reruns after a crash.** Options: (a) rerun the affected part only
  (draft); (b) rerun everything; (c) report the crash as a result if it is a
  system failure (it is, if the product would also crash).

## You test this

1. Check the run log for completeness: every session and question processed
   in every configuration.

## How this number could be lying

- Laptop answers for the full set, phones for a subset; agreement between the
  two on the subset (as in Phase 5.2 Step 14) tells how far laptop results
  describe the phones.

## Verification

- [ ] All configurations run on all v3 data; phones on the fixed subset.
- [ ] Run log with hashes; failures recorded.
- [ ] Automatic scores computed.

## Files changed

- [NEW] `data/results/phase8/` (git-ignored), `docs/results/phase-8/run-log.md`

## Dependencies

- Step 02.

## Common issues

- Accidentally using a non-frozen model file on one phone; check hashes at
  start.
