# Step 10 — Lifecycle Policy (Merge / Forget / Promote) + Storage Stress

## What
A written, testable policy for what happens to memory over time:
- **Merge**: near-duplicate events in the same dwell (e.g. 30 desk events) →
  one event with extended span.
- **Forget**: thumbnails after N days; provisional-only events never refined
  and never retrieved after M days; raw transcripts kept but summarised.
  Forgetting is *soft* first (flag + exclude from search), hard delete only by
  explicit user action (core.md: no silent destructive ops).
- **Promote**: frequently retrieved / ledger-relevant events protected from
  forgetting (MemoryBank-style reinforcement).
- **Storage stress**: replay the full ego_v1 dataset repeatedly to simulate
  ≥ 7 days of capture; measure DB size, query latency growth, and accuracy drift.

## Why
LightMem-Ego explicitly lacks a principled forgetting/merging policy. Without
one, storage and search latency grow without bound, and retrieval gets noisier
(more distractors).

## How to implement
- `src/memories/lifecycle.py` with pure decision functions + a job runner.
- Stress script reuses real recordings (no synthetic memories — core.md real
  data only), shifting timestamps per simulated day and marking them as replay.

## Open decisions
- **Forget signal**: (a) age only — simple, may drop important old facts;
  (b) age × retrieval count (Ebbinghaus-like) — principled, needs usage data;
  (c) user-pinned + (b).

## You test this
- Look at a "what would be forgotten tonight" preview list; mark anything you'd
  be upset to lose. That becomes a regression test.

## How this number could be lying
- Replayed days repeat the same content → merge looks great because days are
  identical. Report merge effect on single real days separately.

## Verification
- [ ] DB size per simulated day + query latency curve over 7+ days.
- [ ] QA accuracy before vs after lifecycle pass (must not drop > 5 %).
- [ ] No hard deletion without explicit user action.

## Files changed
- [NEW] `src/memories/lifecycle.py`, `src/benchmarks/storage_stress.py`, tests

## Dependencies
- Steps 05, 07.
