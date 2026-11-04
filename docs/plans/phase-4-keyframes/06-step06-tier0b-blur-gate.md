# Step 06 — Tier 0b: Blur & Quality Gate

## What
Reject frames that are useless for any model: motion-blurred (variance of
Laplacian below threshold), too dark/overexposed (mean luminance outside
range), or mostly sky/floor/ceiling (optional cheap heuristics). If a burst of
frames is all blurry, keep the *sharpest* in the burst rather than nothing.

## Why
Egocentric video has a high fraction of blurred frames when walking or turning
the head. Captioning them wastes the heavy model and produces garbage memory
("a blurry image of a room").

## How to implement
- `laplacian_var(gray)` via `cv2.Laplacian(..., cv2.CV_64F).var()` on 128×128.
- **Per-session adaptive threshold**: rolling percentile (e.g. reject below the
  20th percentile of the last 60 s) vs a fixed threshold — compare both.
- "Sharpest in burst": when Tier 0a passed but blur rejects N in a row, hold
  the best candidate and emit it when the burst ends.
- Calibrate on ego_v1: label 300 frames sharp/blurry by hand (you), compute
  ROC, pick threshold at chosen precision.

## Open decisions
- **Threshold type**: (a) fixed — simple, breaks across lighting/cameras;
  (b) rolling percentile — adapts, but in a fully blurry walk still passes the
  "least bad"; (c) fixed floor + percentile — both protections, two params.

## You test this
- I give you a labelling page with 300 frames; press S (sharp) / B (blurry) /
  U (useless e.g. ceiling). ~10 minutes. This becomes the calibration set.
- Then look at the 20 frames the gate rejected that you labelled sharp —
  explain what's special about them.

## How this number could be lying
- Laplacian variance is high for noisy dark frames (noise looks like edges) →
  report per lighting; combine with luminance check.
- Hand labels by one person → note it, compute agreement on 50 frames with a
  second labeller if possible.

## Verification
- [ ] ROC curve + chosen operating point saved.
- [ ] Short-event recall drop caused by this gate reported (must be small).
- [ ] Golden fixture decisions added.

## Files changed
- [MODIFY] `src/vision/gates.py`, `tests/test_gates.py`, `src/config.py`
- [NEW] `data/ego_v1/blur_labels.json`

## Dependencies
- Step 05.

## Common issues
- Phone JPEG compression smooths edges → calibrate on phone-captured frames
  from Step 03, not only on the laptop's video files.
