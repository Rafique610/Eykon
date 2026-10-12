# Phase 7 Step 08 — Cost Model and Projection to Real Glasses Parameters

## What

A simple, transparent cost model that predicts, for each split, the energy
per hour on the glasses side and the phone side and the bandwidth needed:

```
E_glasses(split) = E_capture + Σ (stage cost × calls per hour) for glasses-side stages
                   + bytes per hour × radio energy per byte
E_phone(split)   = Σ (stage cost × calls per hour) for phone-side stages
                   + bytes per hour × receive energy per byte
```

- Inputs: measured stage costs (parity gates, Phase 6 telemetry), measured
  calls per hour (Phase 4 / 6 logs), measured bytes per hour (Step 02), measured
  radio energy per byte (Step 03).
- **Validation**: the model's predictions for the R2 rig compared with the
  measured Step 06 energy (error reported).
- **Projection**: plug in published parameters of real glasses (battery
  capacity, chip performance class), clearly marked as projections from
  verified sources (manufacturer data, dated), to estimate glasses battery life
  per split.

## Why

- Even without real glasses, a validated model lets the thesis say which split
  is likely best for glasses and how sensitive that conclusion is to the
  assumptions.
- If route R3 (analysis only) was chosen, this step is the main evidence for
  P4.

## How to implement

1. `src/benchmarks/split_cost_model.py` with inputs from result files (no
   hand-typed numbers except the clearly marked projection parameters).
2. Validation table (predicted vs measured on R2).
3. Sensitivity analysis: vary each assumption ±50 % and see whether the best
   split changes.

## Open decisions

- **Which glasses parameters to project with.** Options: (a) one current
  device's published specs; (b) a range covering several devices; (c) a
  generic "low-power wearable chip" class with ranges. Draft: (b), with sources.

## You test this

1. Read the sensitivity table: is the recommended split the same in most
   scenarios? If not, the thesis says so.

## How this number could be lying

- Published glasses specs are marketing numbers; projections are labelled and
  never presented as measurements.
- A model validated on two phones may not transfer to a glasses chip with a
  different efficiency; the sensitivity analysis shows how much that matters.

## Verification

- [ ] Model implemented with measured inputs.
- [ ] Validation error on R2 measurements reported.
- [ ] Projections with sources and sensitivity analysis.

## Files changed

- [NEW] `src/benchmarks/split_cost_model.py`, `docs/results/phase-7/step08-model.md`

## Dependencies

- Steps 03, 06 (or Step 02 and parity costs for R3).

## Common issues

- Camera capture energy dominates and is hard to separate on a phone;
  estimate it from capture-on vs capture-off runs and label the estimate.
