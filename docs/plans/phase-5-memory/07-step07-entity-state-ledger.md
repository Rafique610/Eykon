# Step 07 — Entity-State Ledger & Invalidation (P2 Core)

## What
From structured records (`objects`, `hand_object`, `place`) and transcripts
("I put the keys in my bag"), extract **state transitions**
`⟨entity, attribute, new_value, t, confidence, evidence⟩`. On a conflicting
transition for the same entity+attribute, close the old row
(`valid_to = t`, `is_current = 0`) and open the new one. Queries about current
state hit the ledger first; historical queries use `valid_from/valid_to`.

## Why
Flat vector search returns both "keys on desk 9 AM" and "keys in bag 2 PM" with
near-identical scores; small LLMs often pick the wrong one. LightMem-Ego's own
limitations: no principled policy for revising/merging memories. This is our
main research contribution in Phase 5.

## How to implement
1. Entity normalisation: alias map + embedding similarity ("car keys", "keys",
   "keychain" → `keys`) — start with a small user-editable list.
2. Transition extraction: rule-based from slots (`hand_object` verbs: put,
   place, insert, take, pick up) + LLM fallback for transcripts.
3. Conflict rule: same entity + same attribute + newer t → invalidate older.
   Low confidence → keep both open and mark `ambiguous`.
4. Answer generation cites the evidence event + thumbnail + time.
5. Retrieval scoring for non-ledger queries:
   `S = [α·dense + (1−α)·BM25] · Φ(t, is_current)` — Φ only applied when the
   query intent is "current state" (Step 08 detects intent).

## Open decisions
- **Extraction source**: (a) VLM slots only — consistent, misses speech-only
  facts; (b) slots + transcripts — fuller, more noise; (c) + explicit user
  voice tags ("remember: keys in drawer") — highest precision, needs user effort.
- **Ambiguity handling**: (a) answer with latest + "last seen" time; (b) list
  both candidates with times; (c) ask a clarifying question.

## You test this
- State-change script on laptop webcam: keys desk → bag (2 min) → jacket
  (5 min) → drawer (8 min). At minute 10 ask "where are my keys?", "where were
  my keys at minute 3?", "where have my keys been today?". Compare against
  ledger-off (flat RAG) answers.

## How this number could be lying
- Scripted moves with clear views are the best case. Include occluded moves
  (put keys in bag while looking elsewhere) — the ledger will miss them; report
  that honestly as the main failure mode.

## Verification
- [ ] State-change accuracy: ledger vs flat RAG on ≥ 40 scripted + unscripted queries.
- [ ] Historical-state accuracy reported separately.
- [ ] Ledger never deletes rows (only closes validity).

## Files changed
- [NEW] `src/memories/ledger.py`, `tests/test_ledger.py`
- [MODIFY] `src/memories/search.py` (Φ weighting), `src/assistant/prompt.py`

## Dependencies
- Steps 01, 03, 04; Phase 4 Step 09 (slots).
