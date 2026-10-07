# Step 04 — Baseline B0: Uniform Sampling, Honestly Measured

## What
Re-run Phase 3's approach (uniform sampling + caption + optional 0.95 dedup)
on the ego_v1 tuning set under wall-clock replay and the emulation profile.
Intervals: 1 s, 2 s, 3 s, 5 s, 10 s. This is the bar every tier must beat.

## Why
A cascade that beats a strawman proves nothing. B0 must be the *best* version
of what we already had, measured with the same metrics the cascade will use.

## How to implement
- `src/benchmarks/keyframe_eval.py` (shared by Steps 04–12):
  - input: run folder (decision log) + `annotations.json`
  - metrics:
    - **heavy calls/hour** (VLM invocations)
    - **short-event recall**: a short event counts as caught if a keyframe
      falls within ±2 s and its caption/slots mention the object
    - **redundancy rate**: fraction of keyframes whose caption embedding has
      cos > 0.9 with the previous keyframe in the same annotated event
    - **live viability**: frames dropped/queued under wall-clock replay,
      max backlog seconds
    - **downstream R@3 / MRR** on the QA set via the existing Phase 1 search
- Run B0 variants: `uniform_{1,2,3,5,10}s` and `uniform_5s_dedup095`.

## You test this
- For `uniform_5s` on the kitchen session, I show you a grid of keyframes with
  the annotated short events marked. You count how many object interactions
  you can actually see in the grid. Your count vs. the metric must agree.

## How this number could be lying
- Short-event recall depends on the caption mentioning the object — a weak
  captioner makes every sampler look bad. Report recall twice: *frame-level*
  (a keyframe exists near the event) and *caption-level* (it was described).
- Batch vs live: report both "offline" numbers and wall-clock numbers; only the
  latter count for live claims.

## Verification
- [ ] All six B0 variants complete on the full tuning set.
- [ ] Metrics script unit-tested on a hand-made toy annotation.
- [ ] Results in `data/results/phase4_b0.json` + summary table in step results.

## Files changed
- [NEW] `src/benchmarks/keyframe_eval.py`
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies
- Steps 01, 02.

## Common issues
- 1 s sampling on 3 h of video with a 13 s/frame captioner = days of compute;
  run caption-level metrics on a stratified subset and frame-level on all.
