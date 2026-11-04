# Phase 8 Step 01 — Final Evaluation Protocol and Code Freeze

## What

1. **Code freeze**: tag the repository state used for all final results
   (e.g. `final-eval-v1`); Android release build with its version and model
   hashes; laptop environment locked (`uv.lock`).
2. **Configuration freeze**: the final configurations (L0–L3 and the default
   product configuration from Gate 3) with manifests and hashes.
3. **Protocol** `docs/results/phase-8/protocol.md`:
   - claims to test, one per row (e.g. "the cascade calls the heavy model fewer
     times per hour than uniform sampling with equal or better short-event
     recall"), each with metric, baseline, data, and the decision rule;
   - data to record (Step 02) with minimum sizes;
   - analysis plan (Step 06): intervals, paired comparisons, worst cases;
   - what changes are allowed after the freeze (bug fixes that do not touch
     evaluated behaviour, recorded with a new tag) and what is not.
4. **Pre-registration**: the protocol committed before any final data is
   recorded.

## Why

- The final numbers must come from a system that did not change while being
  evaluated, on data that did not influence it. A freeze and a written
  protocol are how the panel can trust that.
- Listing claims explicitly makes sure every thesis claim has a test, and no
  test is run without a claim.

## How to implement

1. Collect all frozen configs from earlier phases; resolve any conflicts.
2. Write the claims table from the roadmap research problems (P1–P4),
   conversation results and the LLM-optional conclusion.
3. Tag and commit; record hashes in the protocol.

## Open decisions

- **Which stretch results to include as claims.** Options: (a) none — stretch
  results only as "additional findings"; (b) include those with solid data
  (e.g. Phase 7 model if validated); (c) decide per item with the supervisor.

## You test this

1. Read the claims table. Is there any claim in your planned thesis that has
   no row? Add it or drop the claim.

## How this number could be lying

- A protocol written after seeing earlier results can still be tuned to them;
  the final held-out data (Step 02) protects the numbers, the protocol
  protects the analysis.

## Verification

- [ ] Code, app build and configurations frozen and tagged.
- [ ] Protocol with claims, data, analysis, change rules committed before
      Step 02 recordings.

## Files changed

- [NEW] `docs/results/phase-8/protocol.md`
- [MODIFY] repository tags, `README.md`

## Dependencies

- Phase 5.2 Step 15, Phase 6 Step 15 (and Phase 6.5 / 7 if done).

## Common issues

- Last-minute features after the freeze; they go into "future work", not into
  the evaluated system.
