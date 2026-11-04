# Phase 5.1 Step 08 — Topic Segmentation by Embedding Change

## What

Split a session into topics, reusing the change-detection idea from the
video cascade (roadmap v2: "topic splitting, reusing the change-detection
idea from video"):

1. embed sliding windows of the transcript (e.g. 60 seconds of utterances,
   step 15 seconds) with the existing text embedder,
2. compute the similarity between neighbouring windows; a sharp drop
   suggests a topic change (the same principle as the TextTiling method for
   text, and as Tier 1 novelty for video),
3. pick boundaries with a threshold plus a minimum topic length,
4. give each topic a **title**: L0 by keywords (most distinctive words of the
   topic, e.g. TF-IDF against the rest of the meeting), optionally L2 by the
   generative model (one short line),
5. store `topics` rows (session, start, end, title, title_level),
6. evaluate boundaries against annotated topics (Phase 3.1 Step 11) with
   boundary F1 at ±30 s and ±60 s.

## Why

- Summaries of a 30-minute meeting work better per topic (Step 09): smaller
  inputs, clearer evidence, and summaries that follow the agenda.
- Topics give the user a table of contents for the meeting and let questions
  like "what did we decide about the budget?" route to the right part.
- Reusing the embedding-change idea is a neat, defensible link between the
  video and audio sides of the project (one technique, two modalities).

## How to implement

1. `src/conversations/topics.py`: windowing, similarity curve, boundary
   picking (depth of the similarity valley relative to neighbours), minimum
   topic length.
2. Keyword titles with plain counting (standard library `collections`) and
   a small stop-word list; no new dependency.
3. Optional generative title via the Phase 5.2 answer interface at level L2
   (if not built yet, the current Gemma prompt code), always stored with
   `title_level` so evaluation knows which produced it.
4. Parameters tuned on 2 tuning meetings, evaluated on the others and AMI
   (if AMI topic annotations were converted).
5. Similarity curve plot per session for review.

## Open decisions

- **Embedding model.** Options: (a) the Phase 1 bge-small embedder —
  already on both platforms, no extra RAM; (b) a sentence model tuned for
  topic similarity — maybe better, new model; (c) (a) unless boundary F1 is
  far below the agreement between human annotators.
- **Agenda hints.** Options: (a) none; (b) user types agenda items at session
  start — boundaries can be matched to agenda items (much easier); (c)
  optional agenda field used when present. Draft: (c).

## You test this

1. Look at the similarity curve and the detected topics for one meeting you
   remember well. Do the boundaries match when the agenda changed?
2. Read the keyword titles. Would you recognise each topic from its title?

## How this number could be lying

- Agenda-driven mock meetings change topics more clearly than real
  conversations; results are labelled "mock meetings" and AMI results shown
  separately.
- A ±60 s tolerance is generous for a 30-minute meeting; both tolerances are
  reported.

## Verification

- [ ] Topics stored for all tuning meetings, with titles and levels.
- [ ] Boundary F1 at ±30 s and ±60 s on evaluation meetings.
- [ ] Human agreement on topics (Phase 3.1 Step 11) shown as the ceiling.
- [ ] Plots produced.

## Files changed

- [NEW] `src/conversations/topics.py`
- [MODIFY] `src/conversations/app_page.py`, `src/config.py`
- [NEW] `docs/results/phase-5.1/step08-topics.md`
- [MODIFY] `README.md`

## Dependencies

- Step 07.

## Common issues

- Very short meetings or one-topic lectures produce zero or noisy
  boundaries; a minimum session length for segmentation avoids nonsense.
