# Phase 8 Step 09 — Thesis Writing Plan and Chapters

## What

1. **Outline** following the department template (check the handbook), with a
   draft structure:
   1. Introduction (problem, use cases, contributions, offline constraint)
   2. Background and literature review (Step 08)
   3. Requirements and design (scenario packs, slot schema, LLM-optional design,
      privacy by design)
   4. Data and evaluation methodology (Phase 3.1 dataset, QA taxonomy,
      pre-registration, laptop-vs-phone protocol, parity gates)
   5. Keyframe intelligence (P1, Phase 4, 4.1)
   6. Hierarchical memory and state (P2, Phase 5)
   7. Conversations: meetings and classroom (Phase 5.1)
   8. Answer layer and the LLM question (Phase 5.2)
   9. Live system, scheduling and thermal management (P3, Phase 6)
   10. Glasses and split computing (P4, Phase 7, if done) / people layer
       (Phase 6.5, if done)
   11. Final evaluation (Phase 8 Steps 03–06)
   12. Limitations and negative results (Step 07)
   13. Conclusion and future work
2. **Writing schedule**: chapter by chapter with supervisor review points;
   results chapters reuse the phase results documents (already written in
   plain language).
3. **Figures**: architecture diagrams, cascade diagram, ablation plots,
   accuracy-vs-cost plots, thermal curves, all generated from data.
4. **Plain-language summary** (1 page) for non-specialist readers.

## Why

- Most content already exists in the phase results documents; a plan turns it
  into a coherent argument instead of a collection of reports.
- Early supervisor reviews catch structure problems before final formatting.

## How to implement

1. Choose the writing tool (open decision); set up the template.
2. Write chapters in the order: methodology, results chapters, introduction,
   literature, conclusion (the introduction is easier once results are known).
3. Run the citation check (Step 08) and a "numbers check" (every number in the
   text matches the final results files — a small script comparing numbers
   marked in the text with the result tables).

## Open decisions

- **Writing tool.** Options: (a) LaTeX (Overleaf or local) — standard for CS,
  good for figures and references; (b) Word with the department template —
  if required; (c) Markdown converted to the template — fast drafting, risky
  formatting. Check the handbook first.
- **Length allocation.** Decided with the supervisor once the template's limits
  are known.

## You test this

1. After each chapter, read it aloud for 5 minutes; mark any sentence you
   could not explain to the panel.

## How this number could be lying

- Numbers copied by hand into the thesis drift from the results; the numbers
  check script catches it.

## Verification

- [ ] Outline approved by the supervisor.
- [ ] All chapters drafted and reviewed.
- [ ] Citation check and numbers check pass.
- [ ] Figures generated from data.

## Files changed

- Thesis sources (location chosen with the writing tool), figure scripts in
  `src/benchmarks/figures/`

## Dependencies

- Steps 06–08.

## Common issues

- Writing results before they are final; write methodology first, results
  last.
