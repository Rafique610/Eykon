# Phase 1.1 — Retrieval Quality Improvement

**Goal:** Systematically improve the RAG retrieval pipeline, benchmarking after each change, then pick the best configuration balancing accuracy vs latency.

**Baseline (Phase 1.0, Sep 5 2026):**

| Mode | Hit@1 | Hit@3 | Hit@5 | MRR | P@5 | NDCG@5 |
|---|---|---|---|---|---|---|
| Hybrid | 0.5333 | 0.7667 | 0.7667 | 0.6500 | 0.1933 | 0.5901 |
| Semantic | 0.5667 | 0.7000 | 0.7667 | 0.6333 | 0.1933 | 0.5835 |
| Keyword | 0.3000 | 0.5667 | 0.7000 | 0.4489 | 0.1667 | 0.4387 |

**Primary weakness:** Semantic inference queries (Hit@1 = 0.20, MRR = 0.30 in hybrid mode). The embedding model cannot bridge the gap between abstract queries ("Am I financially comfortable?") and concrete stored text ("15,000 rupees… 2,000 left by month end").

---

## Methodology

Each step:
1. Implement ONE improvement
2. Re-run the same 500-memory / 30-query benchmark
3. Record metrics + latency in a comparison table
4. Keep the change on a feature flag or separate mode so we can A/B compare

After all steps, evaluate the full results and adopt the best configuration permanently.

---

## Steps

| # | Step | What It Does | Expected Impact | Status |
|---|---|---|---|---|
| 09 | [Query Expansion](done/✅%2009-step09-query-expansion.md) | LLM-free keyword expansion before embedding | +0.40 semantic Hit@1 (Actual: 0.60) | ✅ Done |
| 10 | [Widen Retrieval Pool](done/✅%2010-step10-widen-pool.md) | Retrieve top-20 instead of top-5, return top-5 | +0.07 overall Hit@5 (Actual: +0.07) | ✅ Done |
| 11 | [Cross-Encoder Re-ranking](done/✅%2011-step11-cross-encoder.md) | Re-rank top-20 with a cross-encoder model | +0.13 overall Hit@1 (Actual: +0.13) | ✅ Done |
| 12 | [Final Evaluation & Config](done/✅%2012-step12-final-eval.md) | Pick the best combo, set as default, update README | — | ✅ Done |

---

## Dependency Graph

```
Step 09 (Query Expansion)
    ↓  benchmark
Step 10 (Widen Pool)
    ↓  benchmark
Step 11 (Cross-Encoder Re-ranking)
    ↓  benchmark
Step 12 (Final Evaluation)  →  pick winner, lock config
```

Strictly sequential. Each step builds on top of the previous one's code, and each benchmark includes all prior improvements so we can see cumulative impact.

---

## Scoring Criteria for Final Pick (Step 12)

| Criterion | Weight | Why |
|---|---|---|
| Hit@5 (overall) | 30% | The user-facing result quality |
| Semantic Hit@1 | 25% | Our primary weakness to fix |
| MRR (overall) | 20% | How fast we surface the right answer |
| Latency per query | 15% | Must stay under 3s per question on this hardware |
| Model download size | 10% | Demo portability matters for FYP |

---

## Files Created by This Phase

```
src/memories/
├── search.py         (modified — pool widening, re-ranking pipeline)
├── reranker.py       (NEW — cross-encoder wrapper, step 11)
├── query.py          (NEW — query expansion, step 09)
src/benchmarks/
├── run.py            (modified — latency tracking, comparison mode)
```
