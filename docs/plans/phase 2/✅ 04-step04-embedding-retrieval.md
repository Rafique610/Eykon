# Step 04 — On-Device Embedding + Kotlin Retrieval

**Status:** 🔲 Not started  
**Depends on:** Steps 01, 03  
**Blocks:** Step 06

---

## What This Step Does

Wires up an on-device embedding model, implements Phase 1.1's hybrid retrieval
pipeline (Dense + Sparse BM25 + Query Expansion + Cross-Encoder Re-ranking)
entirely on-device in Kotlin.

## Why This Matters

This is the "R" in RAG, ported to Android. As proven in Phase 1.1, plain dense
retrieval fails heavily on abstract semantic queries (20% Hit@1). To maintain
the 93% accuracy achieved on desktop, we MUST port the full pipeline to mobile.
The LLM generation step takes 10-30s anyway, making an extra ~1-2s for 100%
accurate context a critical and worthwhile trade-off.

---

## What Gets Created

```
app/src/main/java/com/eykon/memory/
├── ml/
│   ├── embedder/
│   │   ├── LocalEmbedder.kt         ← Wraps TFLite/LiteRT embedding model (bge-small)
│   │   └── TokenizerHelper.kt       ← Token chunking logic (ported from Phase 1)
│   └── reranker/
│       └── LocalCrossEncoder.kt     ← Wraps ms-marco cross-encoder model via ONNX/TFLite
├── retrieval/
│   ├── QueryExpander.kt             ← Kotlin port of the static CONCEPT_MAP
│   └── SearchService.kt             ← Hybrid search (FTS5 + Dense + RRF + Re-rank)
└── capture/
    └── TextCaptureService.kt        ← (Updated) Now injects real embeddings
```

---

## ⚖️ Decisions to Make

### 1. Retrieval Strategy

| Approach | Pros | Cons |
|---|---|---|
| Plain Dense Retrieval | Fast, simple | Misses abstract semantic inferences (20% Hit@1) |
| Full Phase 1.1 Hybrid | 93% Hit@5, perfect exact | Adds ~1-2s latency, requires second model on-device |

**Recommendation:** Port the full Phase 1.1 Hybrid pipeline. The user correctly identified that plain semantic retrieval performs poorly. The architecture:
1. **Query Expansion:** Pure Kotlin `Map<String, String>` (0ms).
2. **Dense Search:** Brute-force cosine sim over Room DB vectors.
3. **Sparse Search:** SQLite FTS5 (Room natively supports `@Query("SELECT * FROM memories_fts WHERE ...")`).
4. **RRF Fusion:** Pure Kotlin math.
5. **Cross-Encoder Re-ranking:** Re-rank top 20 candidates using a small on-device cross-encoder.

### 2. On-Device Models (Embedding & Cross-Encoder)

We used `BAAI/bge-small-en-v1.5` and `ms-marco-MiniLM-L-6-v2` (~80MB) in Phase 1.

| Framework Option | Notes |
|---|---|
| LiteRT (TFLite) | Standard Android ML path. Requires converting both models from HuggingFace to `.tflite`. |
| ONNX Runtime for Android | Runs HuggingFace models exported to `.onnx` directly with great CPU performance. |

**Recommendation:** If converting the cross-encoder to `.tflite` proves difficult, use **ONNX Runtime Mobile**. It is very widely used for running HuggingFace NLP models (both bi-encoders and cross-encoders) on Android and natively supports `ms-marco` and `bge-small`.

### 3. Sparse Search (BM25)

**Recommendation:** Use Android SQLite's built-in `FTS5`. Room supports creating an FTS entity (`@Entity`, `@Fts5`). This perfectly mirrors Phase 1's SQLite FTS tables and triggers, but implemented via Room annotations.

### 4. Vector Search Implementation

**Recommendation:** Brute-force Kotlin loop.
No NDK/C++ or Vector DB needed. At 1,000 records of 384-dimensions, a `FloatArray` dot-product loop in pure Kotlin takes < 10ms.

---

## How to Implement

### 1. `QueryExpander.kt`
```kotlin
package com.eykon.memory.retrieval

object QueryExpander {
    private val conceptMap = mapOf(
        "morning" to "wake alarm routine breakfast bus shuttle early",
        "financial" to "money rupees allowance budget expenses save cost price",
        // ... port all concepts from Phase 1.1 ...
    )

    fun expand(query: String): String {
        val lowerQuery = query.lowercase()
        var expanded = query
        for ((key, value) in conceptMap) {
            if (lowerQuery.contains(key)) {
                expanded += " $value"
            }
        }
        return expanded
    }
}
```

### 2. Room FTS5 Setup
Update `MemoryRecord.kt` and `MemoryDao.kt` from Step 01 to include FTS5.
```kotlin
@Entity(tableName = "memories_fts")
@Fts5(contentEntity = MemoryRecord::class)
data class MemoryFts(
    @ColumnInfo(name = "text") val text: String
)

// In MemoryDao:
@Query("SELECT memories.* FROM memories JOIN memories_fts ON memories.id = memories_fts.rowid WHERE memories_fts MATCH :query LIMIT :limit")
suspend fun searchFts(query: String, limit: Int): List<MemoryRecord>
```

### 3. `SearchService.kt`
```kotlin
package com.eykon.memory.retrieval

class SearchService(
    private val dao: MemoryDao, 
    private val embedder: LocalEmbedder,
    private val reranker: LocalCrossEncoder
) {
    suspend fun search(query: String, poolK: Int = 20, topK: Int = 5): List<Pair<MemoryRecord, Float>> {
        val expandedQuery = QueryExpander.expand(query)
        
        // 1. Dense Search
        val queryVector = embedder.embed(expandedQuery)
        val denseHits = dao.getAll().map { it to dotProduct(queryVector, it.embedding) }
            .sortedByDescending { it.second }.take(poolK)
            
        // 2. Sparse Search (FTS5)
        val ftsQuery = expandedQuery.split(" ").joinToString(" OR ") { "$it*" }
        val sparseHits = dao.searchFts(ftsQuery, poolK)
        
        // 3. RRF Fusion
        val fusedCandidates = performRrf(denseHits, sparseHits).take(poolK)
        
        // 4. Cross-Encoder Re-rank
        return fusedCandidates.map { record ->
            val score = reranker.rerank(query, record.text) // Original query, not expanded
            record to score
        }
        .sortedByDescending { it.second }
        .take(topK)
    }
}
```

---

## Verification

1. **Unit Test:** Verify `QueryExpander` maps correctly and RRF math works.
2. **Integration:** 
   - Store memories using UI (e.g. "Dentist on 14th", "15,000 rupees monthly allowance").
   - Call `search("Am I financially comfortable?")` (Abstract query).
   - Ensure the "15,000 rupees" memory is retrieved accurately.
3. **Latency Check:** Log the total time taken by `search()`. Ensure it stays under ~2 seconds on the physical device.

---

## Research Notes

- [ ] Evaluate **ONNX Runtime Android** vs **LiteRT** for NLP. ONNX makes porting HuggingFace tokenizers and models significantly easier for Android.
- [ ] Ensure Room FTS5 tokenizer is configured correctly (`tokenizer = "unicode61"` or `porter` if available).
- [ ] Confirm cross-encoder (`ms-marco-MiniLM-L-6-v2`) conversion to `.onnx` or `.tflite` and benchmark inference time on an arm64 Android device.

---

## Files Changed

- `ml/embedder/LocalEmbedder.kt` (new)
- `ml/reranker/LocalCrossEncoder.kt` (new)
- `retrieval/QueryExpander.kt` (new)
- `retrieval/SearchService.kt` (new)
- `data/MemoryRecord.kt` (add FTS entity)
- `capture/TextCaptureService.kt` (modify to use Embedder & Chunking)
