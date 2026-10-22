# Step 05 — Tier 0a: Pixel / Histogram Change Gate

## What
The cheapest filter: on a downscaled grayscale frame (e.g. 64×64 or 128×128),
compute change versus the last *accepted* frame (mean absolute difference
and/or 32-bin histogram χ² distance). Below threshold → drop, no neural work.

## Why
Most egocentric time is near-static (desk, screen, sitting). Dropping those
frames with arithmetic costs microseconds and saves the expensive tiers.

## How to implement
- `src/vision/gates.py`: pure functions on numpy arrays (OpenCV already
  installed): `pixel_delta(prev, cur)`, `hist_chi2(prev, cur)`.
- Compare against last accepted frame, not the previous frame (avoids slow
  drift never triggering).
- Sweep thresholds; for each, record drop rate, short-event recall (frame
  level), and time cost per frame.
- Log `tier0a: drop|pass, value, threshold, µs` per frame.

## Open decisions
- **Signal**: (a) mean abs pixel diff — simplest, sensitive to lighting flicker;
  (b) histogram χ² — robust to small motion, blind to object moved within same
  colours; (c) both with OR — catches more, costs ~2× (still µs).
- **Reference frame**: (a) last accepted; (b) exponential moving average
  background — handles slow lighting change better, slightly more code.

## You test this
- Live laptop webcam page (debug): a number and a red/green dot. Sit still,
  wave a hand, turn the light off/on, put an object down. Tell me where it
  fires when it shouldn't and stays silent when it should fire.

## How this number could be lying
- A mean pixel delta tuned in daylight can fire constantly under flickering
  tube lights at night → evaluate per lighting condition (manifest field).
- Drop rate is meaningless alone — always plotted against short-event recall.

## Verification
- [ ] Threshold sweep curve (drop rate vs recall) saved and plotted.
- [ ] Per-frame cost < 1 ms on laptop emulation profile.
- [ ] Golden fixture expected decisions written for this tier.

## Files changed
- [NEW] `src/vision/gates.py`, `tests/test_gates.py`
- [MODIFY] `src/config.py` (thresholds), `README.md`

## Dependencies
- Steps 02, 04.

## Common issues
- Auto-exposure changes after walking into a room look like big change; consider
  histogram normalisation before diffing.
