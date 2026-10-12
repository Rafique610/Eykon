# Phase 6 Step 05 — Thermal Governor and Operating Modes

## What

A governor that reads the phone's thermal state and switches the pipeline
between operating modes **before** the phone throttles hard:

| Mode | When (draft, tuned per phone) | What changes |
|---|---|---|
| Normal | thermal status none / light, headroom comfortable | full configuration |
| Warm | moderate status or headroom falling | VLM refinement paused; perception rate reduced one step |
| Hot | severe status | perception at minimum rate, cheap path only, no generative answers (templates / quotes only) |
| Critical | critical status | capture paused (audio VAD only, or stop), user notified |

Inputs: `PowerManager` thermal status and, where available, thermal headroom
(a forecast of how close the phone is to throttling), battery temperature;
hysteresis so modes do not flip back and forth.

Experiment: the same 30-minute live workload with the governor off vs on, on
both phones: throttling events, temperature curves, battery, accuracy cost
(frames skipped, events missed, refined records lost).

## Why

- The Infinix already reached 58.9 °C SoC and 4.68 W average in a query-only
  run (handoff facts). Continuous capture will be worse; without a governor
  the phone throttles and everything slows unpredictably.
- Graceful degradation is a concrete answer to the panel's "performance and
  thermal management" component: the system knows its limits and decides what
  to give up first, with measured cost.

## How to implement

1. `ThermalGovernor` (Kotlin): listens to thermal status changes, polls
   headroom every few seconds where supported, computes mode with hysteresis,
   tells the scheduler (Step 04).
2. Mode table in settings (per phone profile); a manual override in the debug
   screen for testing each mode.
3. Each mode change logged with reason; time spent per mode reported.
4. Experiment protocol from Step 01; repeated runs for both phones.
5. Accuracy cost of degradation measured by replaying the same recorded
   session with modes forced, comparing events captured.

## Open decisions

- **Primary signal.** Options: (a) thermal status only — supported on both,
  coarse; (b) headroom forecast — earlier warning, not available on all
  versions / phones; (c) headroom when available, status otherwise (draft).
- **What to give up first.** Options: (a) VLM refinement first (draft);
  (b) perception rate first; (c) answers become templates first. The order
  should follow what users value most; the field study (Step 13) may change
  it.

## You test this

1. Force each mode in the debug screen and watch what changes.
2. Run 30 minutes on the Infinix with the governor off, then (after cooling)
   on. Feel the phone and compare the temperature plots.

## How this number could be lying

- Room temperature strongly affects results; record it and run both
  conditions in the same room on the same day.
- A governor that avoids throttling by doing almost nothing looks perfect on
  temperature; accuracy cost is always reported next to thermal results.

## Verification

- [ ] Governor with hysteresis implemented; mode changes logged.
- [ ] Off vs on comparison on both phones: throttling events, temperature,
      battery, accuracy cost.
- [ ] Time per mode reported.
- [ ] Mode table per phone frozen.

## Files changed

- [NEW] `android/.../live/ThermalGovernor.kt`
- [MODIFY] `android/.../live/Scheduler.kt`, settings
- [NEW] `docs/results/phase-6/step05-thermal.md`
- [MODIFY] `README.md`

## Dependencies

- Step 04.

## Common issues

- Thermal status callbacks are infrequent on some phones; combine with
  polling.
