# Phase 8 Step 05 — Human Evaluation Study with Independent Raters

## What

At least 3 raters other than the developer (classmates; ideally one who does
not know the project) rate system answers on v3:

- blind to configuration and baseline; shuffled order;
- for each answer: correct / partly / wrong (with the written criteria),
  faithful or contains unsupported content, evidence helpful yes / no;
- meeting summaries: the Phase 5.1 faithfulness codes on a sample;
- each item rated by 2 raters; disagreements resolved by a third or reported;
- agreement (Cohen's kappa for pairs, or Krippendorff's alpha for more raters)
  reported.

## Why

- The roadmap's QA KPI is "human-judged"; and the developer's own judgements
  throughout the project are biased by knowing the system. Independent raters
  give the final, credible accuracy numbers.

## How to implement

1. Rating page (Phase 3.1 labelling kit, final mode); rater instructions with
   examples; a 10-item practice round.
2. Sample size: every open-answer question for the default configuration and
   L0; a stratified sample for L1–L3 and baselines (minimum 30 per category per
   configuration where the data allows).
3. Short sessions (at most 60 minutes per rater per day).

## Open decisions

- **Rater compensation / thanks.** Options: (a) volunteers; (b) small thank-you
  (snacks, a coffee); (c) course credit if the department allows.
- **Agreement measure.** Options: (a) pairwise kappa; (b) Krippendorff's alpha
  across all raters (handles missing ratings); (c) both. Draft: (b) with (a)
  for pairs.

## You test this

1. Run the practice round with the first rater; fix unclear instructions.

## How this number could be lying

- Classmates may rate kindly; the faithfulness check (evidence-based) is less
  sensitive to kindness than overall correctness.

## Verification

- [ ] At least 3 independent raters; every item rated twice.
- [ ] Agreement reported; disagreements handled.
- [ ] Ratings stored with rater ids (anonymised).

## Files changed

- [MODIFY] `src/probes/label_app.py` (final rating mode)
- [NEW] `docs/results/phase-8/human-eval.md`

## Dependencies

- Step 03 (and Step 04 for baseline answers).

## Common issues

- Raters reading the gold answer first and anchoring; show the system answer
  and evidence first, gold answer after the first judgement where possible.
