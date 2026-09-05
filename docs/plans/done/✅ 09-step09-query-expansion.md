# Step 09 — Query Expansion

**Status:** 🔲 Not started  
**Phase:** 1.1 — Retrieval Quality Improvement  
**Depends on:** Phase 1.0 complete + benchmark baseline  
**Blocks:** Step 10

---

## What This Step Does

Before embedding a user's question, expand it with semantically related terms to improve retrieval recall. This bridges the vocabulary gap between abstract queries ("Am I financially comfortable?") and concrete stored text ("15,000 rupees monthly allowance").

**No LLM needed.** Uses a static synonym/concept map — zero latency overhead beyond a string concatenation.

## Why This Matters

6 of 10 semantic queries failed in the baseline benchmark. In each case, the query used abstract framing while the stored memory used concrete language. Expanding the query with related concrete terms gives the embedding model a better chance of producing a vector that lands near the relevant chunks.

---

## What Gets Built

### [NEW] `src/memories/query.py`

A single function:

```python
def expand_query(query: str) -> str:
    """Append semantically related terms to improve retrieval recall.
    
    Uses a static concept map of common abstract→concrete expansions
    relevant to personal memory retrieval. Returns the original query
    with expansion terms appended.
    """
```

**Approach — Static Concept Map:**

A dictionary mapping abstract concepts to concrete retrieval terms:

```python
CONCEPT_MAP = {
    "morning":    "wake alarm routine breakfast bus shuttle early",
    "financial":  "money rupees allowance budget expenses save cost price",
    "comfort":    "money budget afford struggle save expense",
    "stress":     "deadline assignment exam pressure sleep tired overwhelmed",
    "cope":       "manage handle sleep tea assignment deadline",
    "social":     "friends group cricket team study hang out",
    "active":     "sport cricket exercise walk activity hobby game",
    "struggle":   "difficult hard grade fail low mark exam",
    "free time":  "weekend hobby game read cricket evening relax",
    "sleep":      "night hours bed alarm wake tired rest",
    "eat":        "food meal lunch dinner breakfast cafeteria canteen",
    "habit":      "routine daily morning evening regular pattern",
    "health":     "sleep eat sick fever clinic exercise stress tired",
    "hobby":      "game cricket read book play weekend evening",
    "study":      "library notes revision exam prepare homework",
    "transport":  "bus shuttle rickshaw walk ride morning commute",
    "room":       "hostel room floor bed desk window furniture",
    "friend":     "omar hassan zara bilal classmate roommate group",
    "professor":  "sir mam teacher class lecture office hours grade",
    "project":    "fyp thesis model training experiment report supervisor",
}
```

**How it works:**
1. Lowercase the query
2. Check each concept key — if any key word appears in the query, append that key's expansion terms
3. Return `f"{original_query} {matched_expansions}"`

No dependency, no model, no API call. Pure string manipulation.

### [MODIFY] `src/memories/search.py`

Add an optional `expand: bool = False` parameter to `search_memories()`. When `True`, run `expand_query()` on the input before embedding.

### [MODIFY] `src/benchmarks/run.py`

Add a `--expand` CLI flag that enables query expansion during the benchmark run. Print results alongside the baseline for comparison.

---

## ⚖️ Decisions You Need to Make

| Decision | Options | Recommendation |
|---|---|---|
| Expansion approach | Static map (no deps) vs LLM-generated (uses Gemma) | Static map — zero latency, testable, no model dependency |
| Where to apply expansion | Before embedding only / Before BM25 only / Both | Before embedding only — BM25 already handles keyword matching |
| Default behavior | Expansion ON by default / OFF (opt-in) | OFF by default — keep backward compat, enable via flag |

---

## Verification

1. Run benchmark WITHOUT expansion → confirm baseline matches existing results
2. Run benchmark WITH expansion → compare Hit@1, MRR for semantic queries
3. Check that exact and multi-hop queries are not hurt by the expansion
4. Measure latency delta (should be <1ms since it's pure string ops)

---

## Expected Results

| Metric | Baseline | Expected with Expansion |
|---|---|---|
| Semantic Hit@1 | 0.20 | 0.30–0.40 |
| Semantic MRR | 0.30 | 0.40–0.55 |
| Overall Hit@5 | 0.77 | 0.80–0.83 |
| Latency delta | — | <1ms per query |

---

## Files

| Action | File | What Changes |
|---|---|---|
| NEW | `src/memories/query.py` | `expand_query()` + `CONCEPT_MAP` |
| MODIFY | `src/memories/search.py` | `expand` parameter on `search_memories()` |
| MODIFY | `src/benchmarks/run.py` | `--expand` flag, comparison output |
