# Step 07 — Tier 0c: IMU Motion Gate

## What
Use gyroscope angular-velocity magnitude (and accelerometer variance) from the
Step 03 traces to (a) suppress frames during fast head/torso turns and (b)
detect "settled after movement" moments — often exactly when something new is
in view (arrived at a room, sat down, looked at an object).

## Why
IMU is nearly free on a phone (sensor hub) and predicts blur *before* the
frame is even analysed. The "settled" signal is a potential keyframe trigger
that pure vision lacks.

## How to implement
- `imu_gate(window)` on a 200–500 ms window aligned to frame timestamp:
  `|ω|` mean/max; pass if below threshold.
- `settle_trigger`: high motion for ≥ T1 seconds followed by low motion for
  ≥ T2 → force-pass next sharp frame to Tier 1.
- Ablation: cascade with and without IMU on the same sessions.

## Open decisions
- **IMU role**: (a) suppression only — safest; (b) suppression + settle
  trigger — may catch arrivals, may add false keyframes; (c) IMU replaces
  Tier 0a when moving — saves pixel work, but fails for head-still/object-moving
  scenes (hands interacting).

## You test this
- Record a 5-min session (Step 03 app): walk, stop and look at a poster, walk,
  sit and look at your desk. Then review which frames the settle trigger picked
  — do they match the moments you "arrived"?

## How this number could be lying
- Chest-mounted vs head-mounted IMU behave very differently; results from one
  mount don't transfer to glasses (Phase 7). Report per mount.
- Laptop experiments use recorded IMU only — no live IMU until the phone gate.

## Verification
- [ ] With/without IMU ablation on all sessions with IMU traces.
- [ ] Blur-rejection workload reduction (frames never reaching Tier 0b) reported.
- [ ] Golden fixtures include IMU windows + expected decisions.

## Files changed
- [MODIFY] `src/vision/gates.py`, `tests/test_gates.py`, `src/config.py`

## Dependencies
- Steps 03, 06.

## Common issues
- Timestamp misalignment of 100+ ms makes the gate look useless → verify sync
  first (Step 03 check).
