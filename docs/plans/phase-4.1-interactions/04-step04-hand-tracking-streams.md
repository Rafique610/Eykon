# Phase 4.1 Step 04 — Hand Tracking for Streams: Smoothing, Handedness, Mount Regions

## What

Turn the Probe B `hands.py` prototype (single frames) into a stream component:

- per-frame hand detection at the cascade's frame rate,
- **temporal smoothing** of landmarks and boxes across frames (so jitter does
  not create fake grasps),
- stable **hand identity** across frames (left / right, or track ids when
  handedness is unreliable),
- **grasp state** per hand (`open`, `closing`, `closed`, `opening`) from
  landmark geometry,
- **mount-aware regions** (chest / head) for where manipulation normally
  happens,
- detection quality metrics: detection rate on frames where annotators saw a
  hand, per lighting and mount.

## Why

- Every later step depends on hands: crops (Step 05), tracking (Step 07),
  the state machine (Step 09), and Phase 4's hand-activity gate (Step 07b).
  Noise here multiplies downstream.
- Probe B's failure list (Step 01 lessons) likely includes "hand not found"
  and "flicker false event". Smoothing and grasp state are the direct fixes.
- Egocentric views (top-down, partly out of frame) are not what hand models
  are usually trained on; we must measure detection on our own frames.

## How to implement

1. **Stream wrapper** in `src/perception/hands.py`: `HandStream` holding the
   last N results; `update(frame, t) -> list[TrackedHand]`.
2. **Smoothing**: exponential moving average on landmark coordinates with a
   reset when the hand disappears for more than a short gap. One parameter
   (alpha) in settings.
3. **Identity**: use the model's handedness when its score is high; otherwise
   match by box overlap with the previous frame.
4. **Grasp state**: mean distance from fingertips to palm centre, normalised
   by hand size; thresholds with hysteresis for open / closed.
5. **Regions**: per-mount polygon (from session `meta.json` mount field);
   a hand outside the region is still tracked but flagged.
6. **Quality labels**: sample 150 frames (seeded, stratified by lighting and
   mount) and label "hand visible: yes/no, grasp: open/closed" with the
   Phase 3.1 labelling kit; compute detection precision / recall and grasp
   accuracy.
7. **Cost**: ms per frame at 640×480, with and without running on every
   frame (rate control as in Phase 4 Step 07b).

## Open decisions

- **Rate.** Options: (a) every frame the cascade passes — best continuity,
  most cost; (b) every second frame with interpolation — half the cost, may
  miss quick grasps; (c) adaptive: every frame while a hand is present,
  sparse when not. Draft: (c), measured against (a).
- **Grasp detection method.** Options: (a) landmark geometry rule (draft) —
  no training, transparent; (b) a tiny classifier on landmarks trained on our
  labels — more accurate, needs labelled data and risks overfitting;
  (c) rule first, classifier only if the rule's grasp accuracy is below the
  Step 01 lesson target.

## You test this

1. Laptop webcam debug view: move your hand in and out of view, open and close
   it, hold your keys. Do the boxes stay stable? Does the grasp state follow
   your hand?
2. Watch the debug contact sheet for one chest-mounted session. Note frames
   where your hand was clearly visible but not detected.

## How this number could be lying

- Detection measured on frames where a human saw a hand ignores frames where
  the hand was half visible and the human also missed it. Labels include a
  "partly visible" option.
- Laptop webcam tests are third-person-like views; the egocentric session
  numbers are the ones reported.

## Verification

- [ ] `HandStream` with smoothing, identity, grasp state, regions; under 300
      lines.
- [ ] Detection precision / recall and grasp accuracy on 150 labelled frames,
      per lighting and mount.
- [ ] Flicker rate (state changes per minute with no annotated event) before
      and after smoothing.
- [ ] Cost per frame for the chosen rate option.

## Files changed

- [MODIFY] `src/perception/hands.py`
- [MODIFY] `src/config.py` (`MEMORY_PERCEPTION_HAND_*`)
- [NEW] `docs/results/phase-4.1/step04-hands.md`
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies

- Step 02 (hand model). Phase 3.1 Step 14 (labelling kit).

## Common issues

- Sleeves or gloves hide the wrist and break handedness; fall back to box
  matching.
- Two hands overlapping (holding a box) merge into one detection; record it
  as a known failure rather than adding complex logic.
