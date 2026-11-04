# Phase 5.2 Step 10 — Scoring: Automatic, Human, and an Optional External Judge

## What

Score every answer from Step 09 using the scoring rules fixed in Phase 3.1
Step 01:

1. **Automatic** where possible: exact match with synonyms (places, speakers,
   yes/no), time tolerance, set overlap (action items), refusal correctness
   (`negative`), evidence correctness (does a cited item fall inside the gold
   evidence range?).
2. **Human** for open answers (summaries, temporal order, recall gists):
   correct / partly / wrong with the written "partly" criteria, plus a
   faithfulness mark (any unsupported claim?), on a blind, shuffled page
   (configuration hidden).
3. **Optional external judge** (an LLM used only as evaluation tooling, never
   at runtime): allowed by roadmap §5.1 if labelled, of a different model
   family than Gemma, and cross-checked against human labels on a subset
   (agreement reported). Follows the Phase 3 Step 12 rules.
4. **Agreement**: second human rater on at least 20 % of human-scored items;
   judge–human agreement if a judge is used.
5. **Calibration**: per configuration, how well `Answer.confidence` predicts
   correctness (reliability tables), feeding Step 01's confidence decision.

## Why

- Automatic scores are cheap and objective but only fit some categories;
  human scores are the ground truth for open answers; a judge can scale human
  scoring but can be biased toward fluent generative text — which is exactly
  the comparison we are making. Hence human scoring is primary.
- Faithfulness is scored separately from correctness: an answer can be right
  by luck and still contain a made-up detail.

## How to implement

1. `src/benchmarks/llm_optional_score.py`: automatic scorers per category.
2. Human scoring page (reuse the Phase 3.1 labelling page, new mode): shows
   question, gold answer, the system answer and its evidence; configuration
   hidden; order shuffled.
3. Sample design for human scoring if time is short: all open-answer items
   for tuning would be ideal; minimum 30 per category per configuration (the
   pessimist rule).
4. Judge (if used): fixed prompt, fixed model, run once, results stored
   separately with a "judge" label.
5. Output: `data/results/phase5.2/scores.jsonl` and agreement tables.

## Open decisions

- **Use an external judge at all.** Options: (a) no — human only, slower,
  cleanest; (b) yes for tuning, human for held-out; (c) yes everywhere with a
  20 % human cross-check. The handoff and roadmap allow (b) or (c) only as
  labelled evaluation tooling.
- **Second rater.** As in previous phases (classmate preferred).

## You test this

1. Score 30 open answers yourself on the blind page; time it.
2. If a judge is used, look at the 10 items where the judge and you disagree
   most. Who is right?

## How this number could be lying

- The user built L0 templates and may unconsciously prefer their style even
  when blind; the second rater checks this.
- A judge from any family may favour longer answers; length is reported next
  to scores.

## Verification

- [ ] Every answer scored (automatic or human); minimum human counts met.
- [ ] Agreement numbers reported (human–human, judge–human if used).
- [ ] Faithfulness marked per answer.
- [ ] Calibration tables per configuration.

## Files changed

- [NEW] `src/benchmarks/llm_optional_score.py`
- [MODIFY] `src/probes/label_app.py` (answer scoring mode)
- [NEW] `data/results/phase5.2/scores.jsonl` (git-ignored)
- [NEW] `docs/results/phase-5.2/scoring.md`
- [MODIFY] `README.md`

## Dependencies

- Step 09.

## Common issues

- Gold answers that are themselves wrong (annotation mistakes) surface here;
  fix them with a logged QA version bump (`qa_v2.x`), and re-score all
  configurations, never only one.
