# Step 11 — Ablation Study B0–B6 (Main P1 Results)

## What
One controlled experiment, same tuning set, same captioner, same metrics,
wall-clock replay under the emulation profile:

| Config | Tiers |
|---|---|
| B0 | Best uniform baseline from Step 04 |
| B1 | Tier 0a only |
| B2 | Tier 0a + 0b |
| B3 | Tier 0a + 0b + 0c (IMU sessions only) |
| B4 | Tier 0a + 0b + Tier 1 (no hysteresis) |
| B5 | B4 + hysteresis + heartbeat |
| B6 | Full cascade + segmenter + structured extraction |

## Why
This table is the core evidence for research problem P1. Each tier must earn
its place; any tier that adds cost without measurable benefit gets removed
(Ponytail applies to research too).

## How to implement
- `task experiment-p4-ablation` loops configs × sessions, writes
  `data/results/phase4_ablation.json`.
- Metrics (from `keyframe_eval.py`): heavy calls/hour, short-event recall
  (frame + caption level, small-object subset separately), redundancy rate,
  boundary F1, R@3/MRR on QA, max backlog, estimated energy proxy
  (Σ tier_cost × count, using per-tier costs measured on the phone later).
- Report mean and **worst session**, with per-scenario breakdown (desk,
  kitchen, walking, night, conversation).
- Statistical check: bootstrap 95 % CI over QA pairs for R@3 differences.

## You test this
- Pick any 2 configs; I generate a side-by-side "memory reel" for a session
  (keyframes + captions). You choose which you'd rather have as your memory,
  blind. Repeat for 5 sessions. Report your preference next to the metrics.

## How this number could be lying
- Tuning and evaluating on the same set inflates every tier → this step is
  *tuning-set* evidence only; Step 12 is the real claim.
- Energy proxy uses laptop costs until Step 13 → label as "proxy".

## Verification
- [ ] All configs on all tuning sessions, JSON + plots saved.
- [ ] CIs reported for key differences.
- [ ] Decision note: which tiers stay, which are dropped, and why.

## Files changed
- [MODIFY] `src/benchmarks/keyframe_eval.py`, `Taskfile.yml`, `README.md`
- [NEW] `docs/additional/phase4-ablation-results.md`

## Dependencies
- Steps 04–10.
