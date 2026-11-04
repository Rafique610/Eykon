# Phase 5.1 Step 10 — Action Item Extraction (Rules and Generative Variants)

## What

Find commitments made in a session ("I'll send the slides by Friday", "Ali
will book the room") with owner, task, due time if said, and the moment it was
said, at two levels:

- **Rules (L0)**: patterns on utterances — first-person future commitments
  ("I will", "I'll", "let me", "I can do"), assignments ("you take", "X will",
  "can you"), agreement replies ("okay, I'll do it") linked to the previous
  utterance, and due-time phrases (reusing the Phase 5 Step 08 time parser).
  Owner = speaker for first-person forms, named person for assignments.
- **Generative (L2)**: per topic, the generative model lists action items
  from the numbered utterances with owner, task, due phrase and the utterance
  id; validated like summary bullets.
- Stored in `action_items` (session, owner_speaker_id, text, due_text,
  t, evidence_json, level, confidence).
- Evaluated against `actions_ref.json` and the paper action lists from
  Phase 3.1 (precision, recall, owner accuracy).

## Why

- "What did I agree to do?" is one of the most useful meeting questions, and
  the `action_items` category is scored by set overlap (Phase 3.1 Step 01).
- Action items are a clear test of whether rules can match a generative
  model: commitments have recognisable wording, so L0 may do well. That is a
  valuable, concrete data point for Gate 3.
- Owner attribution depends on speaker labels; this step shows how speaker
  errors (Step 05) turn into user-visible errors.

## How to implement

1. `src/conversations/actions.py`: `rules(utterances)`,
   `generative(topic_utterances)`; a merge that removes duplicates (same
   owner, similar text, close times).
2. Rule patterns kept in one small list in the file (English only, planning
   default), each with an id so evaluation can show which rule fired.
3. Due-time parsing via `src/memories/temporal.py` (Phase 5 Step 08) when
   available; until then a small regex set, replaced later.
4. Matching to the reference: a predicted item matches a reference item if
   owner matches and text similarity is above a threshold (embedding cosine),
   with a human check on borderline matches during Step 15.
5. "What did I agree to do?" answer: items with owner `me`, newest first,
   each with time and quote.

## Open decisions

- **Owner when speaker is uncertain.** Options: (a) assign the most likely
  speaker; (b) mark owner `unknown` below a confidence threshold (draft);
  (c) list candidates.
- **Including weak commitments** ("maybe I can look at it"). Options:
  (a) include all — high recall, noisy; (b) exclude hedged phrases — cleaner,
  misses some; (c) include with a "tentative" flag (draft).

## You test this

1. For one meeting, compare the system's action items (both levels) with the
   paper list written at the end of that meeting. Which were missed? Which
   are not real commitments?
2. Ask "what did I agree to do?" for that meeting and check the answer.

## How this number could be lying

- Mock meetings with planted action items make commitments unusually explicit;
  results are split by `planted`.
- The reference list itself may miss small commitments; disagreements are
  checked by listening and logged.

## Verification

- [ ] Both levels run on all tuning meetings.
- [ ] Precision, recall and owner accuracy per level, with intervals.
- [ ] Per-rule hit counts for L0.
- [ ] "What did I agree to do?" answer works with evidence.

## Files changed

- [NEW] `src/conversations/actions.py`
- [MODIFY] `src/conversations/app_page.py`
- [NEW] `android/.../conversations/ActionItemsScreen.kt` (or a section of
  the summary screen)
- [NEW] `docs/results/phase-5.1/step10-actions.md`
- [MODIFY] `README.md`

## Dependencies

- Step 07; Phase 5 Step 08 for due-time parsing (optional).

## Common issues

- Questions phrased as commitments ("will you send it?") without an answer:
  only count if a following utterance agrees.
