# Phase 5.2 Step 11 — Cost Measurement: Latency, RAM, Battery, Heat on Both Phones

## What

Measure what each configuration **costs** on the Pixel 9 Pro XL and the
Infinix Note 12, on two workloads:

1. **Capture workload** (perception side): replay the same 30-minute objects
   session at wall-clock speed through the configuration's perception path
   (L0 / L1 / L2 share cheap perception; L3 uses the VLM path). Record
   battery %, current, battery temperature, thermal status changes, peak
   memory, dropped frames, model calls per hour by type.
2. **Question workload** (answer side): 100 fixed questions (a stratified
   subset of the QA set, the same on both phones) answered in each
   configuration from the configuration's database. Record P50 / P90 / worst
   end-to-end latency (tap to answer), peak memory, energy per 100 questions,
   thermal status.
3. **After-session workload** (conversations): one 30-minute meeting
   processed with extractive (L0 / L1) vs generative (L2 / L3) summaries
   (reusing Phase 5.1 Step 11 telemetry).

Protocol: same day, phones cooled to a similar starting battery temperature,
airplane mode, release build (or debug noted), repeated 3 times per
configuration and workload where time allows.

## Why

- Accuracy alone cannot decide Gate 3: a configuration that is 5 % more
  accurate but twice as hot on the Infinix may be the wrong choice for a
  wearable assistant. This is the panel's third complex-computing component
  (performance and thermal management).
- Known so far (handoff): Infinix averaged 4.68 W and 58.9 °C SoC in a
  query-only run; Pixel 4.7 s per query at 1.42 W — LLM queries only, no
  perception. This step fills in the full picture per configuration.

## How to implement

1. Reuse the debug benchmark screen pattern from Phase 3.1 Step 22 and the
   replay harness on device (Phase 4 Step 13).
2. A `ConfigCostRunner` on the phone: loads a configuration database, runs the
   workload, writes telemetry JSON.
3. Cool-down protocol between runs (wait until battery temperature returns
   near the starting value; record the wait).
4. Pull results; `src/benchmarks/llm_optional_cost.py` builds tables:
   configuration × phone × workload × metric, mean and worst of repeats.
5. Measured slowdown factors (laptop vs phone) per configuration added to the
   domain index.

## Open decisions

- **Number of repeats.** Options: (a) 1 — fast, noisy; (b) 3 (draft) —
  shows variation; (c) 5 for the two configurations that matter most after
  Step 12.
- **Battery metric.** Options: (a) battery % drop — coarse; (b) integrated
  current from `BatteryManager` — finer, accuracy varies by phone; (c) both
  (draft).

## You test this

1. Run the question workload yourself on the Infinix in L0 and L2. Note how
   long you waited and how warm the phone got.
2. Compare your impressions with the cost table.

## How this number could be lying

- Short workloads understate sustained throttling; the capture workload is 30
  minutes for this reason, and Phase 6 runs a full day.
- Charging state, screen brightness and background apps change power; all
  fixed and recorded.
- Battery current readings on some phones are averaged over long windows;
  the reading method is stated per phone.

## Verification

- [ ] All four configurations × three workloads × two phones measured (or
      gaps explained, e.g. L3 not runnable on the Infinix).
- [ ] Repeats done; mean and worst reported.
- [ ] Slowdown factors recorded in the domain index.
- [ ] Protocol (temperatures, build type, brightness) recorded.

## Files changed

- [NEW] `android/.../answers/ConfigCostRunner.kt` (debug)
- [NEW] `src/benchmarks/llm_optional_cost.py`
- [NEW] `docs/results/phase-5.2/cost.md`
- [MODIFY] `docs/domain/eykon/index.md`, `Taskfile.yml`, `README.md`

## Dependencies

- Step 08 (configurations and databases); Phase 4 Step 13 and Phase 5.1
  Step 11 (on-device pipelines).

## Common issues

- Configuration databases are large; push once per phone and verify hashes.
- The Infinix may not hold the VLM and the generative model in memory at
  once for L3; record the failure and test a sequential-load variant.
