# Step 01 — Memory Schema v2 + Non-Destructive Migration

## What
Design the SQLite schema for the hierarchy and ledger, and migrate existing
`memories` (Phase 1–3 text/audio/video records) into it **without losing or
altering anything**.

Draft tables (to refine with you):
- `events` (short-term): id, start_ts, end_ts, place, objects_json,
  actions_json, caption, status (`provisional|refined`), keyframe_ids_json,
  source_run, level (`st|lt`), consolidated_into
- `keyframes`: id, event_id, ts, thumb_path (128 px WebP), image_embedding BLOB
- `transcripts`: id, start_ts, end_ts, text, speaker_tag, event_id NULL
- `episodes` (long-term episodic): id, start_ts, end_ts, summary, source_event_ids_json
- `semantic_facts`: id, kind (`routine|preference|relation`), statement,
  support_episode_ids_json, confidence, last_confirmed_ts
- `entity_states`: id, entity, attribute (`location|holder|status`), value,
  valid_from, valid_to NULL, is_current, confidence, evidence_event_id
- text embeddings + FTS index over events/episodes/transcripts/memories

## Why
Everything in Phase 5 depends on this shape. Getting time validity
(`valid_from/valid_to`) into the schema now is what makes state reconciliation
and historical queries ("where was it at 10 AM?") both possible.

## How to implement
- Additive migration in `src/memories/database.py` `init_db()` (idempotent,
  parameterised — core.md). Old `memories` table untouched; a view exposes it to
  the new retrieval layer.
- Backup `data/memories.db` → `data/backups/memories_<date>.db` before first
  migration; verify row counts after.
- Mirror in Android Room with a Room migration + test.

## Open decisions
- **Vector storage**: (a) keep JSON text embeddings + brute force (current
  convention) — simple, fine to ~50k rows; (b) float32 BLOB + brute force —
  4× smaller, faster parse; (c) `sqlite-vec` — ANN-ready, extra native lib on
  Android.
- **FTS**: see roadmap §8 (FTS4 everywhere vs FTS5 + requery lib).
- **Thumbnails**: (a) keep 128 px WebP for N days; (b) keep forever (~4 KB each);
  (c) none — text only, weaker for visual grounding and for your own review.

## You test this
- Review the ER diagram I produce and walk through 3 real questions ("where are
  my keys now", "what did Ali say about the exam", "what do I usually do after
  class") — point at the rows that would answer each.

## How this number could be lying
- A schema that "fits" 3 example questions can fail on categories we didn't
  try → walk all 7 QA categories from Phase 4 Step 01.

## Verification
- [ ] Migration idempotent (run twice, no change).
- [ ] Old memory count identical before/after; old benchmark scores unchanged.
- [ ] Room migration test passes.

## Files changed
- [MODIFY] `src/memories/database.py`, `src/memories/models.py`, Android Room entities/DAO
- [NEW] `docs/additional/memory-schema-v2.md` (ER diagram)

## Dependencies
- Phase 4 Step 10 (event record shape).
