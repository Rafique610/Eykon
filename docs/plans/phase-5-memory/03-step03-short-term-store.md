# Step 03 — Short-Term Event Store + Async Refine/Backfill

## What
Persist closed micro-events immediately as `provisional`, then attach refined
captions, transcripts and OCR **asynchronously** as they become available
(LightMem-Ego's "transcripts and refined descriptions are asynchronously
attached to existing segments"). Embed + index each event as soon as it has
any text.

## Why
Live capture can't wait for the slow model. Writing provisional records keeps
memory queryable within seconds; refinement improves it later without blocking
perception.

## How to implement
- `src/memories/events.py`: `write_provisional(event)`, `attach(event_id, …)`,
  `re_embed(event_id)` (re-index after refinement).
- Background worker with bounded queue (shares policy with Phase 4 Step 09).
- Each update stamped with `updated_at` + `status` so evaluation can measure
  "time-to-useful-memory".

## Open decisions
- **Re-embedding on refine**: (a) replace embedding — simplest; (b) keep both,
  search the max — robust if refinement drifts; (c) only re-embed if text
  changed beyond edit-distance threshold — saves compute.

## You test this
- Replay a 10-min session at wall-clock speed; at minute 3 ask about something
  from minute 1 (provisional) and again at minute 9 (refined). Compare answers.

## How this number could be lying
- Under wall-clock replay on laptop the refine queue may always drain; on the
  phone it may never drain → report queue age P90 on phone at the parity gate.

## Verification
- [ ] Time-to-first-queryable P50/P90 recorded.
- [ ] No event lost when the worker is killed mid-update (crash test).

## Files changed
- [NEW] `src/memories/events.py`, tests
- [MODIFY] `src/memories/service.py`

## Dependencies
- Steps 01–02.
