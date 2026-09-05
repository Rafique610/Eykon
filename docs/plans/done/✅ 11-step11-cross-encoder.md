# Step 11 — Cross-Encoder Re-ranking

**Status:** 🔲 Not started  
**Phase:** 1.1 — Retrieval Quality Improvement  
**Depends on:** Step 10 (Widen Pool)  
**Blocks:** Step 12

---

## What This Step Does

Adds a **cross-encoder re-ranking** stage after the initial retrieval. Instead of ranking by embedding cosine similarity (which computes query and document separately), a cross-encoder sees the full **(query, document) pair** together and produces a relevance score. This catches semantic inference that bi-encoder cosine similarity misses.

## Why This Matters

The core failure of semantic queries is that `embed("Am I financially comfortable?")` and `embed("15,000 rupees... 2,000 left by month end")` produce distant vectors — the bi-encoder doesn't understand inference. A cross-encoder reads both texts together and can reason: "15,000 rupees with 2,000 left = not comfortable" → high relevance score.

This is the **single highest-impact change** for semantic queries.

---

## Architecture

```
          Before (Phase 1.0)              After (Step 11)
          ──────────────────              ──────────────────
Query →   Embed query                    Embed query
          ↓                               ↓
          Dense top-5 + Sparse top-5     Dense top-20 + Sparse top-20 (step 10)
          ↓                               ↓
          RRF fusion → top-5             RRF fusion → top-20 candidates
                                          ↓
                                         Cross-encoder re-rank top-20
                                          ↓
                                         Return top-5
```

The cross-encoder is the **final arbiter** — it only re-ranks, it never retrieves. The initial retrieval (bi-encoder + BM25) acts as a fast first-stage filter.

---

## What Gets Built

### [NEW] `src/memories/reranker.py`

```python
"""Cross-encoder re-ranker for second-stage relevance scoring."""
from __future__ import annotations
from sentence_transformers import CrossEncoder

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker: CrossEncoder | None = None

def get_reranker() -> CrossEncoder:
    """Lazy singleton — loads once, reuses across calls."""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(_MODEL_NAME)
    return _reranker

def rerank(query: str, texts: list[str]) -> list[float]:
    """Score each (query, text) pair. Returns list of relevance scores."""
    model = get_reranker()
    pairs = [(query, t) for t in texts]
    return model.predict(pairs).tolist()
```

**Model choice:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- ~80 MB download (one-time)
- ~22 million parameters (very small)
- Runs on CPU in ~200–400ms for 20 pairs
- Trained on MS MARCO passage ranking — excellent for retrieval re-ranking
- Already installed via `sentence-transformers` (no new dependency)

### [MODIFY] `src/memories/search.py`

Add an optional `rerank: bool = False` parameter to `search_memories()`:

```python
def search_memories(
    query: str,
    embedder: Embedder | None = None,
    top_k: int | None = None,
    mode: str = "hybrid",
    db_path: Path | str | None = None,
    expand: bool = False,       # step 09
    pool_k: int = 20,           # step 10
    rerank: bool = False,       # step 11
) -> list[SearchResult]:
```

When `rerank=True` and mode is `"hybrid"`:
1. Retrieve `pool_k` candidates (existing logic)
2. Run `reranker.rerank(query, [r.record.text for r in candidates])`
3. Sort by cross-encoder score
4. Return top `effective_top_k`

### [MODIFY] `src/benchmarks/run.py`

Add `--rerank` CLI flag. Run benchmark with and without re-ranking for comparison. Track **per-query latency** since re-ranking adds measurable time.

---

## ⚖️ Decisions You Need to Make

| Decision | Options | Recommendation |
|---|---|---|
| Cross-encoder model | `ms-marco-MiniLM-L-6-v2` (80MB) / `ms-marco-TinyBERT-L-2-v2` (17MB, faster) / `ms-marco-MiniLM-L-12-v2` (130MB, better) | `MiniLM-L-6` — best balance of size and quality |
| Re-rank pool size | 10 / 20 / all candidates | 20 — matches pool_k from step 10 |
| Default behavior | Re-ranking ON / OFF | OFF — opt-in via parameter or config |
| Which modes get re-ranking | Hybrid only / Hybrid + Semantic | Hybrid only — keyword mode is intentionally pure BM25 |

---

## Latency Budget

| Stage | Expected Latency | Cumulative |
|---|---|---|
| Query expansion (step 09) | <1ms | ~1ms |
| Embedding query | ~30ms | ~31ms |
| Dense retrieval (top-20) | ~5ms | ~36ms |
| BM25 retrieval (top-20) | ~3ms | ~39ms |
| RRF fusion | <1ms | ~40ms |
| **Cross-encoder re-rank (20 pairs)** | **~200–400ms** | **~240–440ms** |
| **Total with re-ranking** | | **~0.3–0.5s** |
| Total without re-ranking | | ~0.04s |

The cross-encoder is the biggest latency cost. At ~0.3–0.5s per query it's well within the 3-second budget, but it's 10× the retrieval-only latency. This is why it's opt-in.

---

## Verification

1. Run benchmark without re-ranking → confirm cumulative results from steps 09+10
2. Run benchmark WITH re-ranking → compare all metrics
3. Check semantic query improvements specifically (the target weakness)
4. Record per-query latency and verify it stays under 500ms
5. Verify cross-encoder model downloads and loads on first run

---

## Expected Results

| Metric | Baseline | Steps 09+10 | Expected 09+10+11 |
|---|---|---|---|
| Overall Hit@1 | 0.53 | ~0.60 | ~0.70 |
| Overall Hit@5 | 0.77 | ~0.83 | ~0.87 |
| Overall MRR | 0.65 | ~0.70 | ~0.78 |
| Semantic Hit@1 | 0.20 | ~0.40 | ~0.55–0.65 |
| Semantic MRR | 0.30 | ~0.50 | ~0.60–0.70 |
| Avg latency/query | ~40ms | ~45ms | ~300–450ms |

---

## Files

| Action | File | What Changes |
|---|---|---|
| NEW | `src/memories/reranker.py` | `get_reranker()`, `rerank(query, texts)` |
| MODIFY | `src/memories/search.py` | `rerank` parameter, re-ranking pipeline after fusion |
| MODIFY | `src/memories/__init__.py` | Export `rerank` |
| MODIFY | `src/benchmarks/run.py` | `--rerank` flag, latency tracking per query |
