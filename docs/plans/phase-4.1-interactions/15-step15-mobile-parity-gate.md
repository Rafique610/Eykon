# Phase 4.1 Step 15 — Mobile Parity Gate 4.1 (Interaction Tracking on Pixel + Infinix)

## What

Port the frozen cheap perception pipeline to Kotlin and prove it behaves the
same on both phones at a known cost:

- Kotlin packages mirroring Python: `perception/hands`, `cropmatch`,
  `tracker`, `places`, `interactions`, `records`,
- object list and enrolment screen (designed in Step 03), place naming prompt
  (Step 08),
- instrumented test on golden fixtures: hands, crop scores, track ids,
  emitted events and records compared with Python,
- replay of Phase 3.1 phone sessions on both phones at wall-clock rate, with
  per-stage cost, battery temperature, thermal status, peak memory,
- measured laptop-to-phone slowdown per stage.

## Why

- Roadmap §4: a phase is not done until the phone makes the same decisions at
  a known cost.
- The whole point of the cheap path is that it is cheap **on the phone**; only
  this step can show it.

## How to implement

1. **Golden fixtures**: 50 frames with hand landmarks, crop scores, expected
   events (from Step 10 fixtures and Step 12 sessions).
2. **Kotlin port** function-for-function; same model files (hashes checked
   at startup); same preprocessing constants.
3. **Instrumented test** writes `parity_report.json`: hand count agreement,
   top-1 object agreement, event agreement (same object, verb, time within
   tolerance), record field agreement.
4. **Replay**: same sessions as Step 11, both phones, release build if
   possible; measure P50 / P90 per stage, dropped frames, thermal status
   changes, battery drop over a 30-minute replay.
5. **UI**: object list with enrolment via the phone camera; "name this place"
   prompt; airplane-mode check.
6. **Phase 2 fold-in**: confirm text and voice capture and Q&A still work
   with the perception pipeline running (Phase 2 Step 07 integration test,
   folded here as decided 07 October 2026).

## Open decisions

- **Agreement thresholds.** Options: (a) event agreement at least 90 % and
  top-1 object agreement at least 95 %; (b) stricter 95 % / 98 % — matches
  Phase 4's decision agreement; (c) set from the measured Python
  run-to-run variation (if Python itself varies, the phone cannot be
  stricter). Draft: (c), with (a) as the minimum.
- **Image ops on Android**: inherited from Phase 4 Step 13 (OpenCV-Android
  vs Kotlin arrays); use whatever Phase 4 chose.

## You test this

1. On each phone, enrol your keys with the phone camera, then do the
   desk → bag → jacket script live. Ask "where are my keys?" after each move
   (answered by the last-known-state lookup).
2. Run the 30-minute replay with the phone in your pocket; note warmth and
   battery, compare with the report.

## How this number could be lying

- Replay excludes camera sensor power; live power is measured in Phase 6.
- Golden fixtures were chosen from sessions where the laptop pipeline works;
  include 10 fixtures where it fails, to check the phone fails the same way.

## Verification

- [ ] Golden fixture agreement meets the chosen thresholds on both phones.
- [ ] Per-stage cost P50 / P90, thermal, battery, memory on both phones.
- [ ] Measured slowdown factors added to `docs/domain/eykon/index.md`.
- [ ] Enrolment and place naming work on both phones in airplane mode.
- [ ] Phase 2 capture and Q&A still work alongside.

## Files changed

- [NEW] `android/.../perception/` packages, instrumented tests, enrolment and
  place-naming screens
- [NEW] `docs/results/phase-4.1/parity-report.md`
- [MODIFY] `docs/domain/eykon/index.md`, `README.md`, `Taskfile.yml`

## Dependencies

- Steps 11, 12; Phase 4 Step 13 (Kotlin cascade it plugs into).

## Common issues

- MediaPipe Android vs Python versions differ; use the same `.task` file and
  compare landmark outputs on fixtures first.
- Bitmap colour order (ARGB vs RGB) breaks image-text scores silently; check
  embedding cosine against Python on fixtures before anything else.
