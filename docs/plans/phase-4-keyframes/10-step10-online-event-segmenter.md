# Step 10 — Online Event Segmenter (Micro-Events)

## What
Turn the stream of gate decisions + structured records into **micro-events**:
contiguous time spans with a start, end, representative keyframe(s), merged
slots, and (later) attached audio. Online: an event is opened, extended, and
closed as data arrives, never revised by looking ahead more than a small fixed
latency window (e.g. 5 s).

## Why
Memory should be about *events* ("put keys in bag at 14:03 in bedroom"), not
isolated frames. LightMem-Ego segments by temporal continuity and cross-frame
change; EgoLife reports better QA with semantically coherent chunks. Events are
also the unit Phase 5 stores, consolidates and routes.

## How to implement
- `src/vision/segmenter.py`: state machine `IDLE → OPEN → (EXTEND | CLOSE)`.
  Close on: Tier 1 novelty spike, place change in slots, long silence of
  change (heartbeat), max duration cap (e.g. 120 s).
- Event record: `start_ts, end_ts, keyframe_ids[], place, objects (union),
  actions[], hand_object_events[], provisional|refined`.
- Evaluate **boundary F1 at ±2 s and ±5 s** against annotations; also
  over-/under-segmentation ratio.

## Open decisions
- **Boundary signal**: (a) Tier 1 novelty only — simplest; (b) novelty + slot
  change (place/action) — semantic, depends on VLM quality; (c) + IMU settle
  — best guess for arrivals, more params to tune.
- **Allowed look-ahead latency**: (a) 0 s (pure online) — purest claim; (b) 5 s
  — allows "confirm the change persisted", fewer flickers; (c) 15 s — closer to
  offline quality, weakens real-time claim.

## You test this
- Timeline view (Streamlit): annotated events on top, detected events below,
  thumbnails on hover. Scroll through the kitchen and walking sessions and mark
  boundaries you'd call wrong. We tune once with you, then freeze.

## How this number could be lying
- Boundary F1 depends on annotation granularity — a single annotator's "event"
  is subjective. Report F1 at two tolerances and the double-annotated agreement
  from Step 01 as the ceiling.

## Verification
- [ ] Boundary F1 (±2 s, ±5 s) on tuning set.
- [ ] Decision latency per close event ≤ chosen look-ahead.
- [ ] Unit tests for state machine transitions.

## Files changed
- [NEW] `src/vision/segmenter.py`, `tests/test_segmenter.py`
- [MODIFY] `src/ui/` timeline page (split if `app.py` exceeds 300 lines), `README.md`

## Dependencies
- Step 09.

## Common issues
- Flicker (open/close/open within seconds) → minimum event duration + merge
  rule for adjacent events with same place/objects.
