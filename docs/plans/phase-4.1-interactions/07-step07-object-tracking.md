# Phase 4.1 Step 07 — Object Tracking Across Frames

## What

Keep track of each object over consecutive frames so that one physical action
produces one event, and so that identity decisions are made from several
frames instead of one:

- a simple tracker that links per-frame candidates (hand-held object
  identities from Step 05, detector boxes from Step 06 if kept) into tracks,
- per-track identity by **voting** across frames (weighted by confidence),
- track states: `tentative` (seen in 1–2 frames), `confirmed`, `lost`
  (not seen for a short gap), `ended`,
- metrics: track fragmentation (one action split into several tracks),
  identity switches, and the effect on event precision / recall.

## Why

- Single-frame identification flickers (keys, keys, wallet, keys). Voting
  over a track removes most of these flips cheaply.
- One event per action is required for honest event counts: without
  tracking, a 3-second carry can become five "pick-up" events.
- Tracks give the state machine (Step 09) clean inputs: when a held-object
  track ends, something was released.

## How to implement

1. **Tracker** `src/perception/tracker.py`: IoU-based matching of boxes
   (hand-crop boxes and detector boxes) between frames, plus a constant
   velocity prediction (a basic Kalman filter written with numpy, about 50
   lines) for short occlusions. No new dependency (Ponytail: standard
   approach, small code).
2. **Identity voting**: sum of calibrated confidences per object over the
   track; identity = argmax once the track is confirmed; `uncertain` if the
   top-2 are close.
3. **Gap handling**: a track lost for at most N frames (setting) can be
   resumed if a nearby detection with the same identity appears.
4. **Logging**: per-frame track assignments in the run decision log
   (`perception: track_id, object, conf`).
5. **Metrics** on the tuning sessions: tracks per annotated action
   (fragmentation), identity switches per track, and event precision / recall
   with tracking on vs off.

## Open decisions

- **Tracker complexity.** Options: (a) IoU only — simplest, breaks on fast
  motion; (b) IoU + Kalman prediction (draft) — handles short gaps;
  (c) an external tracker such as ByteTrack — stronger, adds dependency and
  licence check, probably unnecessary for one or two hand-held objects.
- **Voting window.** Options: (a) whole track — most stable, identity known
  only at the end; (b) sliding window of N frames — earlier decisions,
  occasional flips; (c) whole track for the final record, sliding window for
  live display.

## You test this

1. Watch the debug video for a tidying session with track ids drawn. Does one
   pick-up keep one id until you put the object down?
2. Note any place where the id changes while you are clearly holding the same
   object.

## How this number could be lying

- Hand-held objects move with the hand, so tracking them is easier than
  general multi-object tracking; numbers do not generalise to tracking
  arbitrary objects.
- Fragmentation measured on scripted moves understates fast natural
  movement; split by `scripted`.

## Verification

- [ ] Tracker under 300 lines, numpy only.
- [ ] Fragmentation and identity switch counts with tracking on vs off.
- [ ] Event precision / recall improvement (or not) reported.
- [ ] Decision log includes track assignments.

## Files changed

- [NEW] `src/perception/tracker.py`
- [MODIFY] `src/perception/runner.py`, `src/config.py`
- [NEW] `docs/results/phase-4.1/step07-tracking.md`
- [MODIFY] `README.md`

## Dependencies

- Step 05 (identities), Step 06 if the detector is kept.

## Common issues

- Camera motion moves every box at once; on a chest mount this is common.
  Use the hand's box as the anchor for held objects rather than absolute
  image positions.
- Track ids reused too fast cause false matches; use increasing ids.
