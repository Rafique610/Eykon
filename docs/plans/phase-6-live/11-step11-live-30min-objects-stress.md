# Phase 6 Step 11 — Live 30-Minute Objects Stress Run on Both Phones

## What

The headline live test for daily-life memory, run on each phone with the
frozen configuration and the chosen scheduler, governor and battery preset:

- **Script**: 30 minutes of a fixed, realistic routine with a printed script
  (similar to the Phase 3.1 state-change scripts, but in a new place): moving
  5 objects between places 10–15 times, walking between rooms, a 5-minute
  desk period, one short conversation, plus 10 questions asked at fixed times
  ("where are my keys?", "did I take my medicine?", "what did Sara say?").
- **Measured** (roadmap §7 KPIs): thermal throttling events, battery drain,
  heavy-model calls per hour, storage growth, answer latency P50 / P90,
  short-event recall and state-change answer accuracy for this run (annotated
  afterwards from a second phone's video or the script), time-to-queryable,
  dropped frames, mode changes.
- **Repeats**: 3 runs per phone if time allows (different days), each
  starting from the protocol state.
- **Conditions**: room temperature recorded; phone on a chest mount; airplane
  mode.

## Why

- This is the result the panel's "thermal management" question is about,
  measured live on a phone for the first time (Phase 3's soak test was a
  fan-cooled laptop at 13.3 s per frame).
- The roadmap's live KPIs (0 throttling events target, at most 15 % battery
  for 30 minutes minimum acceptable on the Pixel) are checked here.

## How to implement

1. Script and question schedule in `docs/results/phase-6/scripts/`.
2. A second phone or camera records the user from the outside (or the script
   is followed exactly and logged by voice notes) for ground truth.
3. Telemetry pulled after each run; `field_report.py` builds the KPI table.
4. Accuracy scored against the script annotations (Phase 3.1 tooling).
5. Results compared with replay-based parity-gate numbers (how much worse is
   live than replay?).

## Open decisions

- **Ground truth source.** Options: (a) follow the script exactly and treat
  it as truth — cheap, small deviations missed; (b) external video recording
  annotated afterwards — accurate, more work; (c) (a) plus voice notes for any
  deviation (draft).

## You test this

1. Do the runs yourself following the script. Write down any moment the app
   felt slow or wrong.
2. After each run, read the KPI table and compare it with what you felt.

## How this number could be lying

- A scripted 30-minute run in a new place is still the developer using their
  own app; Step 14's usability study adds other users.
- Three runs per phone give a rough spread, not a distribution; worst run is
  reported.

## Verification

- [ ] Runs completed on both phones (3 each, or the number achieved).
- [ ] KPI table with all listed metrics; worst run reported.
- [ ] Live vs replay comparison.
- [ ] Results vs roadmap §7 targets and minimums stated plainly.

## Files changed

- [NEW] `docs/results/phase-6/scripts/objects-30min.md`
- [NEW] `docs/results/phase-6/step11-objects-live.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 04–10.

## Common issues

- Phone starting warm from a previous run; follow the cool-down protocol.
