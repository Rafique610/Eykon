# Phase 7 Step 06 — Split-Level Experiments S0–S3

## What

Run the same 30-minute scripted routine (the Phase 6 Step 11 script, a new
place) with each in-scope split, measuring:

- **link**: bytes sent per minute (vs Step 02 predictions), link utilisation,
  drops, gaps;
- **latency**: event to queryable on the hub;
- **energy**: glasses side (compute, camera, radio separated as far as
  telemetry allows) and hub side;
- **accuracy**: short-event recall and state-change answer accuracy for the
  run, compared with the standalone (single-phone) run;
- **thermal**: both devices' temperature and thermal status.

Repeated per split (at least 2 runs each if time allows), both links where
feasible.

## Why

- This is the core evidence for research problem P4: the trade-off between
  glasses battery, link bandwidth and memory quality, measured end to end.

## How to implement

1. Run plan with split × link × repeats; cool-down protocol between runs.
2. Telemetry pulled from both devices; `src/benchmarks/split_report.py`
   builds tables and a trade-off plot (glasses energy vs bandwidth vs
   accuracy).
3. Accuracy scored with the Phase 6 script ground truth.

## Open decisions

- **Splits to run end to end.** Options: (a) S1 and S3 — the two most
  different realistic options; (b) all four; (c) S1, S2, S3 (S0 only
  modelled, since streaming video over BLE is clearly infeasible). Draft: (c)
  if time allows, otherwise (a).

## You test this

1. Do the runs wearing the rig. Which split felt most responsive when you
   asked questions?

## How this number could be lying

- Phone-as-glasses energy is not glasses energy (projected in Step 08).
- The same script repeated becomes easier for the user to perform; order of
  splits randomised.

## Verification

- [ ] All in-scope splits run with repeats; telemetry from both devices.
- [ ] Measured bytes per minute vs Step 02 predictions.
- [ ] Trade-off table and plot.

## Files changed

- [NEW] `src/benchmarks/split_report.py`, `docs/results/phase-7/step06-splits.md`

## Dependencies

- Steps 02, 05.

## Common issues

- One device warming up the other in a pocket; note placement and
  temperatures.
