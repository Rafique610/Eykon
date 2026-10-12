# Phase 8 Step 04 — Baseline Comparisons

## What

Compare the final system with baselines on the same v3 data and questions:

| Baseline | What it is | Compared on |
|---|---|---|
| B-flat | Phase 1 flat RAG over captions (Phase 5 M0) | all QA categories |
| B-uniform | uniform sampling + captioning (Phase 4 B0, best interval) | heavy calls per hour, short-event recall, QA |
| B-phase3 | the Phase 3 pipeline as defended before (1 frame / 5 s, free captions, flat RAG) | everything — shows the progress since the rejected defense |
| Reference design | LightMem-Ego (cloud-based reference) | **positioned, not head-to-head**: our numbers next to their published ones with the differences stated (data, cloud vs on-device models, judge) |

## Why

- The roadmap's final question is "is the whole system better than the
  baselines, honestly?". Without baselines on the same data, no improvement
  claim is valid.
- The Phase 3 baseline shows the panel exactly what changed since the first
  defense.
- LightMem-Ego is the reference design we borrow from; comparing honestly
  (not as if it were the same benchmark) is required by the roadmap (§3,
  Phase 5 Step 11 note).

## How to implement

1. Baseline configurations reproduced from frozen earlier code (tags), run on
   v3.
2. Same scorers; paired comparisons per question.
3. Reference-design table only with numbers verified in the citation ledger
   (Phase 3 Step 16 and Step 08 here), with a column of differences.

## Open decisions

- **Which LightMem-Ego numbers to show.** Options: (a) none, only a
  qualitative comparison; (b) their retrieval and QA numbers with a clear
  "different data, cloud models" warning (draft); (c) only the design
  comparison (what they do vs what we do).

## You test this

1. Read the baseline table and say in one sentence what improved most since
   Phase 3.

## How this number could be lying

- Baselines implemented by us may be weaker than their best versions; B-uniform
  uses the best interval found in Phase 4, and B-flat the full Phase 1
  pipeline with reranking.

## Verification

- [ ] All baselines run on v3 with the same scorers.
- [ ] Paired comparisons with intervals.
- [ ] Reference-design table only with verified numbers and stated
      differences.

## Files changed

- [NEW] `docs/results/phase-8/baselines.md`

## Dependencies

- Step 03; Step 08 for verified reference numbers.

## Common issues

- Old code paths depending on removed files; run baselines from their git tags
  in a separate environment.
