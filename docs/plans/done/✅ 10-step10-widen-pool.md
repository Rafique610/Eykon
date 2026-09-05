# Step 10 — Widen Retrieval Pool

**Status:** 🔲 Not started  
**Phase:** 1.1 — Retrieval Quality Improvement  
**Depends on:** Step 09 (Query Expansion)  
**Blocks:** Step 11

---

## What This Step Does

Currently the hybrid search retrieves **top-5 semantic + top-5 BM25** and fuses them via RRF into a final top-5. The problem: relevant chunks that rank #6–#10 in either list are invisible to the fusion step.

This step widens the retrieval pool to **top-20 from each source**, fuses via RRF, then returns the top-5. The final output size stays the same — the user still sees 5 results — but the fusion has a much richer candidate set to draw from.

## Why This Matters

In several failing queries, the relevant gold chunk was just outside the top-5 in the semantic list (e.g., rank 7 or 8). A wider pool catches these near-misses without any new model or dependency.

---

## What Gets Changed

### [MODIFY] `src/memories/search.py`

Change the pool size from `effective_top_k` to a configurable `pool_k` (default 20):

```python
def search_memories(
    query: str,
    embedder: Embedder | None = None,
    top_k: int | None = None,
    mode: str = "hybrid",
    db_path: Path | str | None = None,
    expand: bool = False,       # from step 09
    pool_k: int = 20,           # NEW: how many to pull from each source
) -> list[SearchResult]:
```

**Specific change in hybrid mode:**
```python
# Before:
pool_size = effective_top_k       # was 5
dense_top = dense_hits[:pool_size]
sparse_top = sparse_hits[:pool_size]

# After:
dense_top = dense_hits[:pool_k]   # now 20
sparse_top = sparse_hits[:pool_k]
# ... same RRF fusion logic ...
return final_results[:effective_top_k]  # still returns 5
```

The RRF score calculation already uses rank position, so wider pools work correctly without formula changes.

### [MODIFY] `src/benchmarks/run.py`

Add a `pool_k` parameter passed through to `search_memories()`. Print the pool size in the benchmark header.

### [MODIFY] `src/config.py`

Add `POOL_K: int = 20` to Settings so it's configurable via `.env`.

---

## ⚖️ Decisions You Need to Make

| Decision | Options | Recommendation |
|---|---|---|
| Default pool size | 10 / 15 / 20 / 30 | 20 — large enough to catch near-misses, small enough to keep latency minimal |
| Apply to all modes? | Hybrid only / All | Hybrid only — semantic and keyword modes don't use fusion |

---

## Verification

1. Run benchmark with pool_k=5 → confirm results match baseline
2. Run benchmark with pool_k=20 → compare Hit@1, Hit@5, MRR
3. Run benchmark with pool_k=20 + query expansion → cumulative improvement
4. Measure latency delta (should be <100ms since it's just comparing more vectors)

---

## Expected Results

| Metric | Baseline | Step 09 | Expected Step 09+10 |
|---|---|---|---|
| Overall Hit@1 | 0.53 | ~0.57 | ~0.60 |
| Overall Hit@5 | 0.77 | ~0.80 | ~0.83 |
| Semantic Hit@1 | 0.20 | ~0.35 | ~0.40 |
| Latency delta | — | <1ms | <50ms extra |

---

## Files

| Action | File | What Changes |
|---|---|---|
| MODIFY | `src/memories/search.py` | `pool_k` parameter, wider candidate pool in hybrid mode |
| MODIFY | `src/config.py` | `POOL_K` setting |
| MODIFY | `src/benchmarks/run.py` | Pass-through `pool_k`, header output |
