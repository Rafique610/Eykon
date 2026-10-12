# Phase 6.5 Step 03 — Face Detection Model Shortlist and Integration

## What

1. **Shortlist** face detection models with the same hard filters as earlier
   shortlists: licence of code and weights read from the licence text and
   usable in an app, on-device phone artifact, laptop runtime, size, speed.
   Candidates to verify: MediaPipe Face Detector (official Android Tasks
   library), BlazeFace-family models, small open face detectors with ONNX or
   LiteRT exports, Android ML Kit face detection (on-device; parity issue with
   the laptop).
2. **Integration** on keyframes only (never on every camera frame), from the
   Phase 4 cascade, on both laptop and phone.
3. **Measure** detection rate on consented test frames (faces at
   conversational distance from a chest / head camera, various lighting),
   false detections, cost per keyframe.

## Why

- Detection is the first step for any face feature; running it only on
  keyframes keeps the cost small (the cascade already reduced frames).
- The licence check matters especially for face models: some are research-
  only.

## How to implement

1. Shortlist table `docs/results/phase-6.5/face-shortlist.md`; licence ledger
   rows.
2. `src/people/faces.py` (new feature folder `src/people/`) and Kotlin
   mirror; same model file both sides.
3. Test frames: from consented sessions only (Phase 3.1 meetings where video
   was agreed), labelled for face boxes on a sample with the labelling kit.
4. Privacy control check: detection runs only when the feature is on.

## Open decisions

- **Detector choice** from the shortlist.
- **Minimum face size.** Options: (a) small (detect faces across the room) —
  more bystanders captured; (b) conversational distance only (draft) — fewer
  bystanders, matches "people I talk to"; (c) user setting.

## You test this

1. With the feature on, sit with a consenting friend; check the debug view
   finds their face in keyframes.
2. Walk through a corridor with strangers; check the minimum-size rule keeps
   distant faces out.

## How this number could be lying

- Detection on posed, well-lit frames is easy; egocentric frames with side
  views and motion are what count; test frames come from real sessions.

## Verification

- [ ] Shortlist with verified licences and phone artifacts.
- [ ] Detector integrated on keyframes on laptop and phone, only when enabled.
- [ ] Detection rate, false detections and cost reported.

## Files changed

- [NEW] `src/people/__init__.py`, `src/people/faces.py`,
  `android/.../people/FaceDetector.kt`
- [NEW] `docs/results/phase-6.5/face-shortlist.md`
- [MODIFY] `docs/results/phase-3.1/licence-ledger.md`, `README.md`

## Dependencies

- Step 02 (go with faces in scope).

## Common issues

- Mirrors and screens showing faces; treat as normal detections and rely on
  user naming to ignore them.
