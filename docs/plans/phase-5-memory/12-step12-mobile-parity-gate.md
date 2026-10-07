# Step 12 — Mobile Parity Gate 5 (Memory Engine on Pixel + Infinix)

## What
Port schema v2, ledger, temporal gating, router and lifecycle jobs to the
Android app; load the same replayed memory DB on both phones; run the M3/M4
evaluation queries on-device and compare answers + latency with the laptop.

## Why
Phase exam (roadmap §4). Memory logic in Kotlin must give the same retrieval
results as Python, and phone latency must be measured, not extrapolated.

## How to implement
- Golden DB fixture: `data/golden/memory_v2.db` + `golden_queries.json` with
  expected top-k event ids and routes.
- Instrumented test: retrieval agreement (top-3 overlap), route agreement,
  ledger answers identical.
- Measure on both phones: retrieval ms, generation s, end-to-end P50/P90,
  RAM, consolidation job duration + battery cost while charging.

## You test this
- On each phone, airplane mode, ask the 15 questions from Step 07/08 tests.
  Rate answers and note how long you waited.

## How this number could be lying
- A golden DB built on laptop has laptop embeddings; the phone embedder may
  differ slightly → also test with embeddings recomputed on the phone.

## Verification
- [ ] Top-3 agreement ≥ 90 %, route agreement ≥ 95 %, ledger answers 100 %.
- [ ] Latency table both phones; Infinix gaps explained.

## Files changed
- [NEW] Android memory v2 packages + instrumented tests, `docs/additional/phase5-parity-report.md`

## Dependencies
- Step 11; Phase 4 Step 13.
