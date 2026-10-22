# Phase 5.1 Step 12 — Conversation Retrieval and Question Answering Integration

## What

Make conversation memory answerable through the same path as everything
else:

1. **Router routes** (Phase 5 Step 09) for conversation intents:
   - `who_said` → utterances search (text + speaker), answer = speaker with
     quote and time,
   - `conversation_recall` → utterances search, answer = quote(s) with
     speaker and time,
   - `action_items` → `action_items` table (filtered by owner and session /
     time window),
   - `meeting_summary` → `summaries` of the session(s) in the time window,
   - `lecture_recall` → utterances plus slide text (Step 13),
   - `negative` → refuse when nothing supports an answer.
2. **Session resolution**: "the project meeting", "yesterday's meeting",
   "the lecture on Monday" resolved to sessions by title, time and topic
   keywords (rules-first, Phase 5 Step 08 parser).
3. **Evidence blocks** for the answer layer: quotes with speaker, time,
   session title and a play link.
4. **Answer levels**: template / quote (L0) by default; generative (L2) when
   the setting is on — via the Phase 5.2 answer interface.

## Why

- Without integration, conversation features are separate screens, not
  memory. Users ask questions in one place; the router must reach
  conversations as easily as objects and events.
- The question categories from Phase 3.1 Step 01 are scored end to end in
  Step 17 through this path.

## How to implement

1. Add intents and routes to `src/memories/router.py` and
   `src/memories/temporal.py` (rules), with tests on 30 questions from the
   tuning QA.
2. `src/conversations/retrieve.py`: session resolver; per-intent evidence
   builders; each under 300 lines.
3. Template answers: e.g. `who_said` → "{speaker} said this at {time} in
   {session}: “{quote}”"; low speaker confidence → "Probably {speaker}…".
4. Wire into the laptop Q&A page and the phone Ask screen.
5. Log route, evidence ids and answer level per question for Step 17.

## Open decisions

- **Session resolution when ambiguous** (two meetings yesterday). Options:
  (a) newest; (b) search both and say which session each answer is from
  (draft); (c) ask the user which meeting.
- **Quotes length.** Options: (a) full utterance; (b) the sentence containing
  the matched words (draft); (c) a window of ±1 utterance for context.

## You test this

1. Ask 10 conversation questions across your tuning meetings on the laptop
   page and 5 on the phone. For each, check route, evidence and answer.
2. Ask one question about a meeting that never happened. Does it refuse?

## How this number could be lying

- Questions written by the user who knows the meetings are easier to route;
  external-author questions (Phase 3.1 Step 12) are reported separately.

## Verification

- [ ] All conversation intents routed; 30-question route check passes or
      failures are listed.
- [ ] Template answers with evidence for each intent.
- [ ] Works on laptop and Pixel with no network.
- [ ] Logs ready for Step 17.

## Files changed

- [NEW] `src/conversations/retrieve.py`
- [MODIFY] `src/memories/router.py`, `src/memories/temporal.py`
- [MODIFY] laptop Q&A page, `android/.../ui/screens/AskQuestionScreen.kt`
  (and its ViewModel)
- [MODIFY] `README.md`

## Dependencies

- Steps 07–10; Phase 5 Steps 08–09; Phase 5.2 Step 01 (answer interface)
  for the generative level.

## Common issues

- Question words like "say" or "told" appear in non-conversation questions
  ("the sign said…"); the router's rule list includes counter-examples.
