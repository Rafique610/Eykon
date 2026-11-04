# Phase 5.1 Step 09 — Chunked Summaries with Evidence Links

## What

Produce a meeting summary in which **every line points to the moments that
support it**, at two answer levels so Phase 5.2 can compare them:

- **Extractive summary (L0, no generative model)**: per topic, select the
  most representative utterances (e.g. those closest to the topic's centre
  embedding, plus utterances containing decision words such as "decided",
  "agreed", "deadline"), shorten them by removing filler words, and present
  them as bullets with speaker and time. Every bullet is quoted text.
- **Generative summary (L2)**: per topic, the small generative model (Gemma 4
  E2B via the Phase 5.2 answer interface) writes 1–3 bullets from **only that
  topic's utterances**, each bullet followed by the utterance ids it used;
  then a short merge step builds the meeting-level summary of 5–10 bullets.
- **Evidence check (both levels)**: each bullet's cited utterances must exist
  and lie inside the topic; for generative bullets, a cheap support check
  (embedding similarity between bullet and cited utterances above a
  threshold) flags likely unsupported bullets.
- Stored in `summaries` (session, topic, bullet, evidence_json, level,
  support_score, flagged).

## Why

- Roadmap v2: "chunked summaries and action items, each line linked to its
  timestamp". Evidence links are what make a summary checkable, which is the
  only defensible way to use a small model for summarisation.
- Chunking by topic keeps the input small enough for a 2B model on a phone
  and reduces made-up content (the model sees only what it summarises).
- The extractive variant is the LLM-free baseline the panel asked about. If it
  is close in faithfulness and usefulness, the generative model is not needed
  for summaries; if not, we know exactly what it adds.

## How to implement

1. `src/conversations/summarise.py` with `extractive(topic)` and
   `generative(topic)`; meeting-level merge for each.
2. Generative prompt: strict instructions ("use only these lines; cite line
   ids after each bullet; if nothing important, write nothing"), utterances
   numbered with ids, speaker names, times. Parse citations; bullets without
   valid citations are flagged, not dropped silently.
3. Support check: similarity between bullet and concatenated cited
   utterances; threshold set on 2 tuning meetings, reported, not tuned on
   evaluation meetings.
4. Long topics: split into chunks below the model's comfortable context size
   (measured on the phone, not assumed), summarise chunks, then merge.
5. Laptop page and phone screen: bullets with "play" links for each cited
   moment.
6. Cost: tokens in and out, latency per topic, on the laptop emulation profile
   (phone in Step 18).

## Open decisions

- **Extractive selection method.** Options: (a) centroid closeness only —
  simple, misses decisions said once; (b) centroid plus decision-word rule
  (draft) — catches decisions, language-specific; (c) a small extractive
  model (Phase 5.2 L1) — possibly better, adds a model.
- **What to do with flagged bullets.** Options: (a) hide them; (b) show them
  marked "check this" (draft) — honest; (c) regenerate once — more compute,
  may still fail.
- **Summary per speaker.** Options: (a) no; (b) "what each person said" section
  when speaker labels are usable (scope rule); (c) only for "me".

## You test this

1. Read both summaries (extractive and generative) for one meeting you
   attended, without knowing which is which (the page shuffles them). Which
   would you rather receive after a meeting?
2. Click through every evidence link of one summary. Does each bullet match
   what was said?

## How this number could be lying

- Fluent generative bullets feel correct even when wrong; Step 15 audits them
  against the evidence, not by fluency.
- The support check is itself a model similarity; it catches some
  unsupported bullets, not all. Its precision and recall are measured in
  Step 15.
- Mock meetings with planted facts favour summaries that repeat planted
  facts; summary bullets are compared against the reference including the
  `planted` tag.

## Verification

- [ ] Both levels produce summaries for all tuning meetings, with valid
      evidence links.
- [ ] Citation parse rate and flagged-bullet rate for the generative level.
- [ ] Cost per meeting (tokens, latency) recorded.
- [ ] Blind preference by the user recorded for at least 3 meetings.

## Files changed

- [NEW] `src/conversations/summarise.py`
- [MODIFY] `src/conversations/app_page.py`, `src/config.py`
- [NEW] `android/.../conversations/SummaryScreen.kt`
- [NEW] `docs/results/phase-5.1/step09-summaries.md`
- [MODIFY] `README.md`

## Dependencies

- Step 08 (topics); Phase 5.2 Step 01 (answer interface) — if not ready, use
  the existing `src/assistant/` prompt code and switch later.

## Common issues

- The model cites ids that do not exist or ranges outside the topic; validate
  and flag, never "fix" by guessing ids.
- Speaker names inside the prompt make the model attribute statements to the
  wrong person when labels are uncertain; include speaker confidence and tell
  the model to write "someone" for low-confidence speakers.
