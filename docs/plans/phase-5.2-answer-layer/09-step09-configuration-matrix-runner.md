# Phase 5.2 Step 09 — Configuration Matrix Runner on All Scenario Questions

## What

Run every question in the QA set through every configuration and store every
answer with its full record:

- **Questions**: all 11 categories from `qa_v2.json` (tuning), plus the
  held-out questions written in Phase 4 Step 12, Phase 4.1 Step 12 and
  Phase 5.1 Step 17; reported separately.
- **Configurations**: L0, L1, L2, L3 (Step 08), plus the adaptive `auto`
  variant if Step 01 chose it.
- **Output**: `data/results/phase5.2/answers.jsonl` — one line per question ×
  configuration: answer text, level used, evidence ids, confidence, refused,
  timings, model calls, configuration manifest hash.
- **Pre-written results structure**: the empty tables and the conclusion
  template for Step 15 are written **before** the run (which tables, which
  comparisons, what counts as "LLM needed" for a category — for example "L2 or
  L3 better than the best of L0 / L1 by more than the confidence interval
  width, at acceptable cost").

## Why

- This is the experiment the whole of roadmap v2 §3 asks for: same data, same
  questions, four configurations.
- Writing the decision rule and the table structure before seeing results is
  the same protection as the Phase 3.1 pre-registration; Gate 3 is too
  important to be decided by post-hoc reading of tables.

## How to implement

1. `src/benchmarks/llm_optional_eval.py`: loads questions, applies each
   configuration, calls `answer(...)`, writes JSONL incrementally, resumable.
2. Laptop runs under the Mobile Emulation Profile (CPU only, fixed threads).
   Phone cost is measured separately in Step 11 on a subset.
3. Run order randomised per question (seeded) so model warm-up or heat does
   not always hit the same configuration.
4. Decision rule and result template committed to
   `docs/results/phase-5.2/preregistration.md` before the first run.
5. Sanity checks: each configuration's zero-generative-call guarantee (L0 /
   L1), database manifest match, no question missing.

## Open decisions

- **"LLM needed" rule.** Options: (a) accuracy gain larger than the
  confidence interval width; (b) accuracy gain of at least X percentage
  points (user sets X) and faithfulness not worse; (c) (b) plus a cost limit
  (e.g. the L2 / L3 latency P90 on the Pixel within the roadmap KPI). The user
  chooses before the run.
- **Include `auto`.** Options: (a) yes, as a fifth configuration — tests a
  practical design; (b) no — keep the clean four; (c) later, only if L0 and L2
  split the categories clearly.

## You test this

1. Before the run, read the pre-registered decision rule and say it in your
   own words.
2. After the run, pick 5 random questions and read all four answers side by
   side (configuration hidden). Guess which is which.

## How this number could be lying

- Laptop answers differ slightly from phone answers (runtime, threads); the
  phone subset in Step 11 and the parity gate in Step 14 check the size of
  this effect.
- Held-out question sets come from different phases and authors; they are
  reported per source.

## Verification

- [ ] Pre-registration committed before the first run.
- [ ] Every question × configuration answered (count check), held-out
      separate.
- [ ] Zero generative calls in L0 / L1 confirmed from records.
- [ ] Runner resumable; results JSONL complete with manifests.

## Files changed

- [NEW] `src/benchmarks/llm_optional_eval.py`
- [NEW] `docs/results/phase-5.2/preregistration.md`
- [NEW] `data/results/phase5.2/answers.jsonl` (git-ignored)
- [MODIFY] `Taskfile.yml` (`llm-optional-run`), `README.md`

## Dependencies

- Step 08; QA sets from Phase 3.1, 4, 4.1, 5.1.

## Common issues

- L3 runs are slow because every answer loads the generative model; keep the
  model loaded across questions within a configuration.
