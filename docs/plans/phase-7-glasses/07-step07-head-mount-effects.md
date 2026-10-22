# Phase 7 Step 07 — Head-Mount Data Effects on the Cascade and Perception

## What

Measure how moving the camera from the chest to the head (as glasses would)
changes the earlier components, on the same activities:

- Tier 0 / IMU gate behaviour (head motion is faster and more frequent),
- blur rates (Tier 0b rejects),
- hand visibility and hand-gate / path C accuracy (hands appear lower and
  smaller from the head, or not at all when looking up),
- Tier 1 novelty and keyframe counts,
- place recognition and object answers.

Data: paired sessions (chest and head worn at the same time where possible,
otherwise the same script twice), plus any head-mounted sessions from
Phase 3.1 (mount open decision) and EPIC-KITCHENS (head-mounted) as an
external reference.

## Why

- All tuning so far used mostly chest mounts; glasses see what the eyes see.
  If thresholds do not transfer, the glasses recommendation must include
  re-tuning.
- Roadmap Phase 4 Step 07 already warned that chest and head IMU behave
  differently; this step quantifies it.

## How to implement

1. Record paired sessions with two phones (chest and head) using the Phase 3.1
   protocol; annotate short events once (shared ground truth).
2. Run the frozen pipelines on both; compare per component.
3. If a component degrades badly, test one re-tuned threshold set and report
   both (never replace the frozen results).

## Open decisions

- **Re-tuning allowed?** Options: (a) no, report degradation only;
  (b) one re-tuning pass on head data with a separate held-out head session
  (draft); (c) full re-tuning (too large for a stretch phase).

## You test this

1. Watch the head and chest keyframe reels for the same 5 minutes side by
   side. Which one shows your hands and objects better?

## How this number could be lying

- Wearing two phones changes how a person moves; note it.

## Verification

- [ ] Paired sessions recorded and annotated.
- [ ] Per-component comparison chest vs head.
- [ ] Re-tuning (if any) on separate data with held-out check.

## Files changed

- [NEW] `docs/results/phase-7/step07-head-mount.md`

## Dependencies

- Step 04; Phase 4 and 4.1 frozen pipelines.

## Common issues

- Head strap slips and points the camera down; check frames at the start of
  each session.
