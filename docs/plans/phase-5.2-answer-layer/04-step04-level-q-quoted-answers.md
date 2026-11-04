# Phase 5.2 Step 04 — Level Q: Quoted-Text Answers

## What

Answers made of **exact quotes** from memory, chosen and lightly framed, with
no generated words beyond a fixed frame:

- conversation questions (`conversation_recall`, `who_said`,
  `lecture_recall`): the best 1–3 utterance sentences (or slide text), with
  speaker, time and session;
- text memories (Phase 1 notes, voice memos): the best matching sentences;
- event questions without a template: the best event caption or slot text;
- summary questions: the Phase 5.1 extractive summary bullets (quotes).

Sentence selection: split candidate utterances / texts into sentences, score
each sentence against the question (embedding similarity plus keyword
overlap from the existing hybrid search), pick the top sentences, keep
neighbouring sentences when a sentence is too short to stand alone.

## Why

- Quotes cannot be unfaithful: they are exactly what was said or written. For
  conversation questions this is the LLM-free alternative to a generated
  answer, and the most trustworthy one.
- Phase 1 already showed strong retrieval on text (Hit@5 93.33 %); quoting
  the retrieved text directly tests how far good retrieval alone gets us.
- Comparing level Q with level G on conversation questions is one of the
  clearest tests of what a generative model adds (rephrasing, combining
  several quotes, answering "why" questions).

## How to implement

1. `src/answers/quotes.py`: `best_sentences(question, evidence_items, k)`,
   with sentence splitting by punctuation and pause boundaries (utterances
   already have times).
2. Scoring reuses `src/memories/` embedder and BM25 code; no new model.
3. Frame text: "{speaker} at {time}: “…”"; multiple quotes listed in time
   order.
4. Confidence: top sentence score and its margin over the next.

## Open decisions

- **Number of quotes.** Options: (a) 1 — short, may miss context; (b) up to 3
  (draft); (c) adaptive by score gap.
- **Light cleanup of quotes** (removing "um", repeated words). Options:
  (a) none — exact; (b) remove filler words only — more readable, still
  faithful (draft); (c) none in stored evidence, cleanup in display only.

## You test this

1. Ask 10 conversation questions at level Q. Is the answer in the quote? Is
   the quote too long or too short?
2. Ask a "why" question ("why did we move the deadline?"). Does a quote
   answer it, or would you need a summary?

## How this number could be lying

- Questions written from the transcript reuse its words, which favours
  keyword-based sentence selection; external-author questions are reported
  separately.

## Verification

- [ ] Level Q works for all listed intents.
- [ ] Sentence selection reuses existing retrieval code.
- [ ] Tuning accuracy per intent recorded.

## Files changed

- [NEW] `src/answers/quotes.py`
- [NEW] `docs/results/phase-5.2/step04-quotes.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 01, 02; Phase 5.1 Step 07 (utterances), Step 09 (extractive
  summaries).

## Common issues

- Transcription errors inside quotes ("deadline" heard as "dead line"); show
  the play link so the user can listen.
