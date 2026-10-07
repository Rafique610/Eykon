# Step 01 — Egocentric Evaluation Dataset v1

## What
Build the dataset every later experiment in Phases 4–6 is measured on:
egocentric recordings (mostly ours), annotated with event boundaries, short
events, object-state changes, spoken content, and a QA set with gold evidence
timestamps. Stored under `data/ego_v1/` with a manifest.

## Why
Phase 3's evidence came from 3 stock clips of ~20 s and 9 QA pairs — any
conclusion was a coin toss. Keyframe gating, memory and state tracking can only
be judged on long, messy, first-person footage with known ground truth. Without
this step every later number is meaningless.

## How to implement
1. **Recording protocol** (`data/ego_v1/PROTOCOL.md`): phone mounted on chest
   or head (cheap clip/strap), 30 fps native, scripted + unscripted sessions.
   Target ≥ 3 hours total split into sessions of 10–30 min:
   - desk work / study (static, long dwell — tests over-sampling)
   - kitchen / room tidying (many short object interactions)
   - walking indoors/outdoors (motion blur, IMU)
   - conversation with a friend/family member (consent!) (audio recall)
   - night / low light session
   - "state-change scripts": keys desk → bag → jacket; wallet; passport;
     charger — each move timestamped by voice ("keys into bag") for annotation.
2. **Annotation** (`data/ego_v1/<session>/annotations.json`):
   - `events`: start/end s, label (coarse activity)
   - `short_events`: timestamp, object, action, from → to location
   - `state_changes`: entity, old_state, new_state, t
   - `speech`: t, speaker, gist (for audio recall questions)
   Tool options in Open decisions.
3. **QA set** (`data/ego_v1/qa.json`) ≥ 150 pairs, each with category and gold
   evidence time range:
   `object_location_now`, `object_location_past`, `short_event`,
   `temporal_order` ("before/after"), `conversation_recall`,
   `activity_summary`, `negative` (thing never seen → must say "don't know").
4. **Split**: tuning set (≈ 70 %) vs. **held-out set recorded later**
   (Step 12). The held-out set is never opened during tuning.
5. **Privacy**: consent from anyone recorded; no bystander faces published;
   dataset stays local, git-ignored.
6. Optional public subset — see Open decisions.

## Open decisions
- **Annotation tool**: (a) CVAT (local docker) — proper timeline UI, heavy
  setup; (b) ELAN — designed for time-aligned video annotation, light, exports
  XML we must convert; (c) a tiny Streamlit page in our app — zero new deps,
  matches our stack, but we build it.
- **Public data**: (a) none — fully our use case; (b) Ego4D NLQ/episodic-memory
  subset — gives comparability but needs a license and huge downloads;
  (c) EPIC-KITCHENS-100 — dense action boundaries, great for boundary F1,
  kitchen-only.
- **Mount**: (a) chest strap — stable, misses what eyes see; (b) head strap —
  closest to glasses, more blur; (c) both for one session to quantify the
  difference (useful for Phase 7 argument).

## You test this
1. Record the first 10-minute "state-change script" session using the protocol.
2. Watch it back at 2× and write down every short event you notice that the
   script didn't plan — this calibrates how much annotation misses.
3. Write 10 QA pairs yourself; I write 10 from the annotations; we compare
   whether my questions sound like real questions you'd ask.

## How this number could be lying
- Scripted sessions are easier than real life → at least 40 % unscripted.
- One person annotating → boundary noise. Double-annotate one session and
  report inter-annotator agreement.
- QA written by the same person who tunes thresholds leaks knowledge → QA for
  the held-out set is written before any tuning results are seen.

## Verification
- [ ] ≥ 3 h recorded, ≥ 6 sessions, all scenario types covered.
- [ ] ≥ 150 QA pairs, every category ≥ 15 pairs.
- [ ] Manifest lists duration, fps, resolution, mount, lighting, consent flag.
- [ ] One session double-annotated, agreement reported.

## Files changed
- [NEW] `data/ego_v1/PROTOCOL.md`, `data/ego_v1/manifest.json`, `data/ego_v1/qa.json`, per-session `annotations.json`
- [MODIFY] `.gitignore` — ensure raw video in `data/ego_v1/` is ignored

## Dependencies
- None. Can start immediately, in parallel with Phase 3 Steps 11–16.

## Common issues
- Phone overheats recording 30 min at 4K → record 1080p/30.
- Audio of other people without consent → do not record.
- Storage: ~3 h 1080p ≈ 15–25 GB; keep originals off the repo.
