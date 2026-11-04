# Phase 6 Step 15 — Phase 6 Results and Gate 4 Contribution

## What

1. **Results document** `docs/results/phase-6/results.md`: all live KPIs vs
   roadmap §7 targets and minimums, per phone; scheduler and governor
   experiments; battery presets; privacy and network-zero evidence;
   robustness; field study; usability study; live vs replay gaps.
2. **Gate 4 input** (roadmap v2 §6: "do results hold on both phones?"): a
   table of every phase's parity gate result (Phases 4, 4.1, 5, 5.1, 5.2)
   plus the live Phase 6 results, with a verdict per component: holds on both
   / holds on Pixel only / degraded on Infinix (with the mode it needs) /
   fails.
3. **Measured slowdown factors** consolidated in `docs/domain/eykon/index.md`
   (one table, all components, both phones).
4. **Issues carried to Phase 8**: anything that failed or remains unclear.
5. **Annotations**: master roadmap (Gate 4 outcome), Phase 7 overview (which
   pipeline cut points are realistic given phone costs), Phase 8 overview
   (which live results the thesis can claim).

## Why

- Gate 4 decides what the final thesis can claim about phones. Bringing every
  parity gate together in one table makes the answer clear and checkable.
- Phase 7 (glasses) depends on phone-side costs to choose where to split the
  pipeline.

## How to implement

1. Tables generated from telemetry reports and parity reports (no retyping).
2. Verdict rules written before filling the table (for example "holds" means
   within the parity gate's tolerance and meeting the minimum KPI).
3. Supervisor review of the Gate 4 table; outcome recorded.

## Open decisions

- **What to claim about the Infinix.** Options: (a) "supported in low-end
  mode" with numbers — honest; (b) "not supported" for components that fail —
  honest, narrower; (c) per component (draft).

## You test this

1. Read the Gate 4 table; for each "holds on both", recall the run that showed
   it. If you cannot, the evidence link is missing.
2. Decide which live demo you would show the panel, based on the most robust
   results.

## How this number could be lying

- Combining many results into one verdict table hides detail; every cell links
  to its source report.

## Verification

- [ ] Results document with all live KPIs vs targets, per phone.
- [ ] Gate 4 table with verdict rules written first; supervisor review
      recorded.
- [ ] Slowdown factors consolidated in the domain index.
- [ ] Roadmap, Phase 7 and Phase 8 overviews annotated.

## Files changed

- [NEW] `docs/results/phase-6/results.md`, `docs/results/phase-6/gate4.md`
- [MODIFY] `docs/domain/eykon/index.md`, `docs/plans/00-roadmap.md`,
  `docs/plans/phase-7-glasses/00-*.md`, `docs/plans/phase-8-final/00-*.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 11–14; all parity gates.

## Common issues

- Missing parity results from a skipped phase (e.g. Phase 4.1 reduced); state
  "not applicable" with the reason rather than leaving blanks.
