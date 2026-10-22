# Step 08 — Temporal Query Understanding + Time-Window Gating

> [!NOTE]
> **Roadmap v2 — 07 October 2026 (addition):** rules-first is the default
> (roadmap v2: "the router and time parser stay rules-first"). The LLM
> fallback is behind a setting and is off in Phase 5.2's L0 and L1
> configurations; its benefit is measured as "parse accuracy with and without
> fallback". English only (planning default), so the Urdu time words mentioned
> below are out of scope unless that default changes. Intents gain
> `who_said`, `action_items`, `meeting_summary`, `lecture_recall` from the
> Phase 3.1 taxonomy.

## What
Parse each question into `{intent, time_window, anchors, entities}`:
- explicit ("yesterday at 3", "this morning") → absolute window;
- relative anchors ("after the pharmacy, before lunch") → resolve anchor events
  via search, derive `[t1, t2]`;
- intent: `current_state | past_state | event_recall | conversation | summary | negative`.
Apply `WHERE start_ts BETWEEN t1 AND t2` **before** dense/BM25 ranking, and
inject the current timestamp into the prompt as an anchor.

## Why
Embeddings don't understand time; `new_Dev.md` and EgoLife both flag temporal
ordering as a top failure. Gating by SQL is cheap and exact.

## How to implement
- Rule-based parser first (regex + small dictionary of time words, English +
  common Urdu time words if used); LLM parse fallback only when rules fail.
- Anchor resolution: top-1 event for anchor phrase, with confidence; if low,
  fall back to ungated search.
- `src/memories/temporal.py` + tests with a fixed "now".

## Open decisions
- **Parser**: (a) rules only — fast, predictable, limited; (b) Gemma JSON parse
  — flexible, +1–3 s on phone; (c) rules then LLM fallback.

## You test this
- Ask 20 time-based questions you'd naturally ask about a replayed day; I show
  the parsed window for each before the answer. Mark parse correct/wrong.

## How this number could be lying
- Questions written by us match our rules → include questions from another
  person who hasn't seen the rules.

## Verification
- [ ] Parse accuracy on ≥ 50 temporal questions (incl. external author).
- [ ] Temporal-order QA accuracy: gated vs ungated.

## Files changed
- [NEW] `src/memories/temporal.py`, tests
- [MODIFY] `src/memories/search.py`, `src/memories/query.py`

## Dependencies
- Steps 01, 03.
