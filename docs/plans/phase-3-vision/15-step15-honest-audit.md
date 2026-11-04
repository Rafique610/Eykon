# Step 15 — Phase 3 Honest Audit ("How our numbers could be lying")

## What
A written, evidence-backed audit of every Phase 3 result (A1–A8): what it
actually proves, what it does not, and what experiment would turn it into real
evidence. Output: `docs/additional/phase3-honest-audit.md`.

## Why
The panel already rejected one defense. A strict panel will find these holes
themselves; it is far stronger if we name them first and show the plan that
closes each one (Phases 4–6). It also stops us from building Phase 4 on
assumptions that were never really tested (e.g. "5 s sampling is enough").

## How to implement
1. For each experiment, fill this table from the real result JSONs in `data/`
   (`experiment_results.json`, `soak_test_results.json`,
   `vision_benchmark_results.json`, A5/A6/A7/A8 outputs):

   | Exp | Claim we made | Data behind it (n videos, minutes, QA pairs, device) | What it really proves | What it does NOT prove | Closing experiment (phase/step) |
   |---|---|---|---|---|---|

2. Known items to include (from `.memory/16-september-2026/tasks.md`):
   - **A1**: cosine similarity of 256M/500M Q8 captions vs F16 (0.809 / 0.864) —
     measures similarity, not correctness. Closing: human caption audit
     (Phase 3 Step 11 note, Phase 4 Step 08).
   - **A2**: 3 clips of ~10–20 s; at 5 s interval that is **2 frames per clip**;
     9 QA pairs. Closing: Phase 4 Step 03 (uniform baseline on ≥ 3 h of
     egocentric video, ≥ 150 QA).
   - **A3**: short vs long captions on the same 9 QA pairs; Hit@3 = 1.00 for
     both → ceiling effect, cannot discriminate. Closing: Phase 4 Step 08.
   - **A4**: 30.21 min, 136 frames, 13.32 s/frame, +1.2 % drift, laptop with
     active cooling. Proves no memory leak in the captioner loop on a laptop.
     Does not prove phone thermals, and shows the captioner runs at
     **0.075 fps** — far from live. Closing: Phase 6 Steps 06–07.
   - On-device KPI runs (02 Oct): Pixel 4.7 s/query, 1.42 W avg; Infinix
     11.1 s/query, **4.68 W avg, 58.9 °C SoC** — these are query-only, no
     perception running. Closing: Phase 6.
3. Add a "statistical power" paragraph: with 9 QA pairs, one answer changes
   accuracy by 11 percentage points. State a minimum n for future claims (≥ 30
   per condition, roadmap §5.1).
4. Add "What we are still confident about" — honest strengths (end-to-end loop
   works fully offline on a real phone; hybrid retrieval benchmark on 499
   memories / 30 QA; zero leaks in soak).

## You test this
- Read the audit and mark each row **agree / too harsh / too soft**. Anything
  "too soft" gets rewritten. You are the first panel member.
- Pick the 3 weakest claims and say them out loud as if answering the panel;
  if an answer feels weak, it becomes an item in the Phase 4 plan.

## How this number could be lying
This step *is* the pessimist check. Its own risk: being so harsh it hides real
strengths — so section 4 is mandatory.

## Verification
- [ ] Every Phase 3 claim in `.memory/` and plan docs appears in the table.
- [ ] Every row has a closing experiment mapped to a Phase 4–6 step.
- [ ] Numbers are copied from result files, not from memory (core.md: real data only).

## Files changed
- [NEW] `docs/additional/phase3-honest-audit.md`

## Dependencies
- Steps 11, 12, 14 (so their results are included).

## Common issues
- Results JSONs may be overwritten between runs — read, don't regenerate.
- Don't "fix" weak results here by re-running quietly; re-runs belong in the
  mapped closing experiment.
