# Phase 5.2 Step 12 — Per-Question-Type Analysis and Failure Taxonomy

## What

Turn scores (Step 10) and costs (Step 11) into the tables pre-registered in
Step 09:

1. **Main table**: category (11 rows) × configuration (L0–L3): accuracy with
   intervals, faithfulness rate, refusal correctness for `negative`; tuning
   and held-out separately.
2. **Cost table**: configuration × phone: latency P50 / P90, memory, energy,
   thermal events, model calls per hour.
3. **Accuracy vs cost plot** per category group (objects, events and time,
   conversations, summaries).
4. **Paired comparisons** per category: for each question, which
   configurations got it right (counts of "only L2 right", "only L0 right",
   both, neither).
5. **Failure taxonomy** per configuration, each wrong answer coded:
   `memory_missing` (the fact was never stored), `retrieval_miss` (stored but
   not found), `wrong_route`, `stale_state`, `template_gap` (no template
   fits), `quote_irrelevant`, `generation_unsupported` (made-up content),
   `generation_wrong_reasoning`, `wrong_refusal`, `missed_refusal`.
6. **Where the LLM helps**: categories where the pre-registered rule says
   L2 / L3 is needed, and **why** (from the paired comparisons and failure
   codes — e.g. "combining several quotes", "answering why-questions").

## Why

- Gate 3 is per question type (roadmap v2 §6: "for which question types?").
  An overall average would hide that, for example, templates win on object
  locations while generation wins on summaries.
- The failure taxonomy separates memory problems (which no answer level can
  fix) from answering problems (where levels differ), so the conclusion
  blames the right component.

## How to implement

1. `src/benchmarks/llm_optional_report.py`: all tables and plots generated
   from `scores.jsonl` and cost files; no hand-typed numbers.
2. Failure coding on the human scoring page (new mode), second rater on 20 %.
3. Results document `docs/results/phase-5.2/results.md` filled into the
   pre-written template; deviations from the template listed explicitly.

## Open decisions

- **How to report categories with too few held-out questions.** Options:
  (a) omit held-out for that category; (b) report with a "small sample"
  warning and the interval (draft); (c) merge similar categories for the
  held-out table only.

## You test this

1. Read the main table and say, for each category, which configuration you
   would use in your own app.
2. Read 5 examples of `generation_unsupported`. Would they have misled you?

## How this number could be lying

- Category sizes differ; overall averages are weighted by category size and
  shown next to unweighted averages.
- Failure coding by the person who built the system may favour "memory" codes
  over "my template" codes; the second rater checks.
- L0 object results depend on whether Phase 4.1 was in scope; the table
  states which perception L0 used.

## Verification

- [ ] All pre-registered tables and plots generated.
- [ ] Paired comparisons per category.
- [ ] Failure taxonomy counts per configuration with agreement on 20 %.
- [ ] "Where the LLM helps" section written from the numbers.

## Files changed

- [NEW] `src/benchmarks/llm_optional_report.py`
- [NEW] `docs/results/phase-5.2/results.md`, `docs/results/phase-5.2/*.csv`,
  plots
- [MODIFY] `README.md`

## Dependencies

- Steps 10, 11.

## Common issues

- Mixing tuning and held-out numbers in one table; keep them in separate
  columns everywhere.
