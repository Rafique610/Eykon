# Step 12 — Held-Out Real-World Gauntlet

## What
Freeze all thresholds and models. Record **new** sessions (≥ 1 h total) that
were never seen during tuning, write their QA before running anything, then run
B0 vs. the chosen cascade once. These are the numbers that go in the thesis.

## Why
Every threshold so far was tuned on data we looked at. Real deployment sees new
rooms, new lighting, new people. If the cascade's advantage disappears here,
it was overfitting — and we must know before building Phase 5 on top of it.

## How to implement
1. Freeze config → `data/results/phase4_frozen_config.json` (hash recorded).
2. You record ≥ 4 new sessions in **places not used before** (e.g. a friend's
   house, university library, a shop, outdoors at dusk).
3. Annotate + write QA (≥ 50 pairs) **before** running the pipeline.
4. Single run: B0 vs frozen cascade, same metrics as Step 11.
5. Write a "generalisation gap" table: tuning-set vs held-out for every metric.

## You test this
- You do the recordings and the QA writing.
- After the run, you use the Streamlit memory UI to ask 15 questions live of
  the held-out memory and score each answer correct/partly/wrong — this is
  the "does it actually feel useful" check.

## How this number could be lying
- Re-tuning after seeing held-out results silently turns it into a tuning set.
  Any change after this step requires a **new** held-out recording.

## Verification
- [ ] Config hash unchanged between freeze and run.
- [ ] QA file timestamp earlier than first pipeline run.
- [ ] Generalisation gap table written, including where the cascade lost.

## Files changed
- [NEW] `data/ego_v1/heldout/…`, `docs/additional/phase4-heldout-results.md`

## Dependencies
- Step 11.
