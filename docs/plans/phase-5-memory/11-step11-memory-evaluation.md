# Step 11 — Retrieval & QA Evaluation v2 (Main P2 Results)

## What
One controlled comparison on the ego_v1 QA set (tuning + held-out reported
separately):

| Config | Description |
|---|---|
| M0 | Flat RAG — current Phase 1 pipeline over event captions (our baseline) |
| M1 | Hierarchy (cur/st/lt) + router, no ledger, no temporal gating (≈ LightMem-Ego-style design, but on-device) |
| M2 | M1 + temporal gating |
| M3 | M2 + entity-state ledger |
| M4 | M3 + lifecycle policy applied |

Metrics: R@1/3/5, MRR (comparable in kind to LightMem-Ego's table, **not**
head-to-head since data differs), QA accuracy (LLM-judge + human on a subset),
per-category accuracy, P50/P90 latency, evidence tokens per answer.

## Why
This is the core evidence for P2 and the table the panel will look at.

## How to implement
- `src/benchmarks/memory_eval.py`, bootstrap CIs, per-category breakdown,
  failure taxonomy (retrieval miss / wrong level / stale state / hallucination).

## You test this
- Blind human scoring of 60 answers (mixed configs). You don't know which
  config produced which answer.

## How this number could be lying
- If the LLM judge is the same family as the answering model (Gemma), it may
  favour it → use a different-family judge and report human agreement.
- Don't compare our numbers to LightMem-Ego's as if same benchmark; state the
  differences (data, cloud vs on-device models).

## Verification
- [ ] All configs on tuning + held-out QA; CIs reported.
- [ ] Failure taxonomy with counts and 3 examples each.

## Files changed
- [NEW] `src/benchmarks/memory_eval.py`, `docs/additional/phase5-results.md`

## Dependencies
- Steps 01–10.
