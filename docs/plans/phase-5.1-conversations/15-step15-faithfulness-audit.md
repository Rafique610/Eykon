# Phase 5.1 Step 15 — Human Faithfulness Audit of Summaries and Error Taxonomy

## What

A blind human audit of every summary bullet, action item and lecture note
produced for the evaluation sessions, at both levels (L0 extractive, L2
generative):

- each bullet / item judged against its cited evidence **and** the full
  transcript:

  | Code | Meaning |
  |---|---|
  | `supported` | stated in the cited moments |
  | `supported_elsewhere` | true, but the citation is wrong |
  | `unsupported` | not said anywhere (made up) |
  | `distorted` | said, but changed (wrong number, negation, scope) |
  | `wrong_speaker` | content right, attributed to the wrong person |
  | `trivial` | true but unimportant (filler) |

- coverage: which reference summary bullets and reference action items are
  **missing** from the system output,
- counts per code and level, per condition (clean / noisy / overlap), with
  intervals; the support-check flag (Step 09) evaluated as a detector of
  `unsupported` bullets,
- a second rater on at least 20 % of items for agreement.

## Why

- Roadmap v2 exit criterion: "at least 10 meetings or lectures judged by
  humans, error types counted". Summaries are where small generative models
  are most likely to invent content; the panel will ask.
- Counting **types** of error (made up vs wrong speaker vs distorted) tells us
  whether to blame the model, the transcript or the speaker labels.
- Comparing levels on faithfulness is a direct input to Gate 3 (is the LLM
  needed for summaries?).

## How to implement

1. Audit page (laptop, Streamlit, separate file or a mode of the Phase 3.1
   labelling page): shows one bullet at a time, its cited utterances with
   audio, and a searchable transcript; level hidden; order shuffled.
2. Reference coverage pass: for each reference bullet / action item, the rater
   marks which system bullet (if any) covers it.
3. Analysis script: counts, rates, intervals, per condition and level;
   support-check precision / recall as a detector of `unsupported`.
4. Gallery of 5 examples per code.

## Open decisions

- **Second rater.** Options: (a) a classmate — independent; (b) the user a
  week later — available, weaker; (c) a participant of the meeting — knows
  what was said, may be biased. Draft: (a) where possible.
- **Weighting.** Options: (a) count every bullet equally; (b) weight by
  importance (rater marks key / minor) — closer to user impact; (c) report
  both (draft).

## You test this

1. Audit at least one full meeting yourself; time it.
2. Look at the `unsupported` gallery: would any of these have misled you in
   real life?

## How this number could be lying

- Raters who attended the meeting fill gaps from memory and mark
  `supported` too easily; the cited-evidence check is done first, from the
  audio only.
- If the extractive level only quotes, it can never be `unsupported`; its
  weakness shows up as missing coverage and `trivial` bullets, which are
  therefore reported next to faithfulness.
- Large-model evaluation tools (an external LLM judge) are not used here; if
  added later as evaluation tooling only, they are labelled and cross-checked
  against these human labels (roadmap §5.1).

## Verification

- [ ] All evaluation sessions audited (at least 10 sessions overall).
- [ ] Counts per code, level and condition with intervals.
- [ ] Coverage (missing reference items) per level.
- [ ] Agreement on at least 20 % with a second rater.
- [ ] Support-check detector precision / recall.

## Files changed

- [NEW] `src/benchmarks/conversation_audit.py`, audit page
- [NEW] `docs/results/phase-5.1/faithfulness-audit.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 09, 10 (and 14 for lecture notes).

## Common issues

- Auditing is slow; budget about 1 minute per bullet and plan sessions of at
  most an hour.
