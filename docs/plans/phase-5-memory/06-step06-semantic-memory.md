# Step 06 — Semantic Memory (Routines & Preferences) — Exploratory

## What
Derive higher-level facts from many episodes: routines ("usually at the library
after 2 PM on weekdays"), preferences, relationships. Each fact stores its
supporting episodes and a confidence that grows with confirmations and decays
without them.

## Why
LightMem-Ego includes semantic memory for routine discovery. It's a strong demo
feature but needs multi-day data — so it is explicitly **exploratory**: done
only if Steps 01–05 and 07–09 are on track.

## How to implement
- Periodic pass over episodes: frequency of (place, time-of-day, weekday,
  activity) tuples → candidate routines (plain counting first; LLM only to
  phrase them).
- `semantic_facts` with `support_episode_ids`, `confidence`, `last_confirmed_ts`.

## Open decisions
- **Extraction**: (a) counting + templates — transparent, limited; (b) LLM over
  episode summaries — richer, harder to verify; (c) counting proposes, LLM
  phrases — middle ground.

## You test this
- After ≥ 5 days of field data (Phase 6), read the discovered routines and mark
  true/false/creepy-but-true (the last is a privacy signal).

## How this number could be lying
- 5 days is too little for real routines; report support counts with each fact.

## Verification
- [ ] Every fact traceable to ≥ 3 supporting episodes.
- [ ] Precision of facts judged by you.

## Files changed
- [NEW] `src/memories/semantic.py`, tests

## Dependencies
- Step 05; needs multi-day data (Phase 6 Step 10) to evaluate properly.
