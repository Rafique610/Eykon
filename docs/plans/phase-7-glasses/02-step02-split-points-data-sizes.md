# Phase 7 Step 02 — Split Points and Data Sizes per Split

## What

For each split S0–S3, compute **how many bytes per minute** would cross the
link, using real pipeline logs rather than estimates:

- S0: compressed video at the capture settings (measured file sizes from
  Phase 3.1 recordings at the product resolution) + audio;
- S1: keyframes that pass Tier 0 (counts from Phase 4 decision logs × JPEG
  size at the chosen quality) + VAD speech segments (audio bytes);
- S2: Tier 1 embeddings (dimension × bytes) for frames passing Tier 0, plus
  crops / thumbnails for novel frames;
- S3: slot records (JSON size, measured) + occasional thumbnails.

Per scenario (desk, kitchen, walking, meeting), mean and worst minute.

## Why

- Bandwidth needs decide which links are feasible (BLE is slow, Wi-Fi Direct
  faster but more power-hungry); measured data sizes make that comparison
  concrete.
- Using our own logs ties Phase 7 to the actual cascade instead of
  textbook numbers.

## How to implement

1. `src/benchmarks/split_sizes.py` reading Phase 4 / 4.1 run folders and
   Phase 3.1 session folders.
2. Tables and a bar chart per split and scenario; worst-minute values
   highlighted.

## Open decisions

- **JPEG quality for S1.** Options: (a) the capture quality used so far
  (Phase 3.1, quality 90); (b) lower (e.g. 70) to save bandwidth — may hurt
  extraction; (c) measure extraction accuracy at two qualities on a sample.

## You test this

1. Look at the worst-minute table: which scenario sends the most in S1? Does
   that match what you would expect?

## How this number could be lying

- Data sizes from replay logs may differ from live capture (Phase 6 logs are
  preferred where available).

## Verification

- [ ] Bytes per minute per split and scenario, mean and worst, from real
      logs.

## Files changed

- [NEW] `src/benchmarks/split_sizes.py`, `docs/results/phase-7/step02-sizes.md`

## Dependencies

- Step 01; Phase 4 / 4.1 / 6 logs.

## Common issues

- Embedding sizes depend on float format; report float32 and a compressed
  (float16 or 8-bit) variant.
