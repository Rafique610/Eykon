# Phase 5.2 Step 02 — Evidence Model and Citation Rendering

## What

Define what "evidence" is and how it is shown:

- **Evidence item** types:
  - `frame` — keyframe thumbnail path, time, session, place;
  - `time_range` — start and end, with what happened (event label);
  - `quote` — utterance text, speaker, time, session, play link;
  - `state` — ledger row (entity, value, valid from, confidence, evidence
    frame);
  - `slide` — slide keyframe with OCR text;
  - `summary_bullet` — bullet with its own evidence.
- Each item has a stable id, a source record id, and a short human label.
- **Renderers**: plain text (for logs and the laptop CLI), Streamlit
  components (laptop), and the Kotlin design for the phone (Step 13): a
  thumbnail strip, quote cards with play buttons, a "last seen" card.
- **Citation format** used by all levels: `[e3]` markers in answer text that
  refer to evidence ids, validated on output.

## Why

- Roadmap v2 design principle 4: "every answer shows time, picture or quoted
  words". One evidence model shared by all levels makes this true for L0 and
  L3 alike.
- Validated citation markers are how generative answers are kept checkable;
  invalid citations become a measurable faithfulness signal (Step 10).
- Users trust answers they can verify; showing a thumbnail and time for
  "your keys are in the bag" is the core UX of the product.

## How to implement

1. `src/answers/evidence.py`: dataclasses, `from_router_block(block)`,
   `render_text(items)`, `validate_citations(text, items) -> list[problem]`.
2. Streamlit components in a separate page file (not `src/ui/app.py`).
3. Thumbnails: reuse keyframe thumbnails from Phase 5 schema (`keyframes`
   table), never re-extract frames at answer time.
4. Play links: session id + time; the laptop page seeks the audio player;
   phone behaviour designed for Step 13.
5. Privacy: evidence of excluded or deleted records is never rendered (check
   status flags from Phase 5 lifecycle).

## Open decisions

- **How many evidence items to show.** Options: (a) top 1 — clean, may hide
  the needed context; (b) top 3 (draft); (c) all used, collapsed after 3.
- **Citation markers visible to users.** Options: (a) visible `[1]` markers
  linked to cards — transparent; (b) hidden, cards listed below — cleaner
  text; (c) visible on laptop, hidden on phone.

## You test this

1. Ask 5 questions on the laptop page; for each, click every evidence item.
   Does it show what the answer claims?
2. Ask about something you deleted (lifecycle) and confirm its evidence never
   appears.

## How this number could be lying

- Showing evidence does not make an answer correct; the evidence may be
  irrelevant to the claim. Step 10 scores evidence relevance separately.

## Verification

- [ ] All evidence types implemented with text rendering and Streamlit
      rendering.
- [ ] Citation validation catches missing and unknown ids (tested on crafted
      examples).
- [ ] Deleted / excluded records never rendered.
- [ ] Files under 300 lines.

## Files changed

- [NEW] `src/answers/evidence.py`, `src/answers/evidence_page.py`
- [MODIFY] `README.md`

## Dependencies

- Step 01; Phase 5 Step 01 (keyframes, ledger tables), Phase 5.1 Step 07
  (utterances).

## Common issues

- Thumbnails missing because lifecycle removed them (Phase 5 Step 10); show
  "thumbnail expired" with the time, never a broken image.
