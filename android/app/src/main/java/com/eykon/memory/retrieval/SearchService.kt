package com.eykon.memory.retrieval

import com.eykon.memory.data.MemoryDao
import com.eykon.memory.data.MemoryRecord
import com.eykon.memory.ml.embedder.LocalEmbedder
import com.eykon.memory.ml.reranker.LocalCrossEncoder
import kotlin.math.sqrt

class SearchService(
    private val dao: MemoryDao,
    private val embedder: LocalEmbedder? = null,
    private val reranker: LocalCrossEncoder? = null
) {
    suspend fun search(query: String, poolK: Int = 20, topK: Int = 5): List<Pair<MemoryRecord, Float>> {
        val expandedQuery = QueryExpander.expand(query)
        val allMemories = dao.getAll()
        if (allMemories.isEmpty()) {
            return emptyList()
        }
        
        // 1. Dense Search (when embedder is configured and memories have embeddings)
        val denseHits = if (embedder != null) {
            val queryVector = embedder.embed(expandedQuery)
            allMemories
                .filter { it.hasEmbedding }
                .map { it to dotProduct(queryVector, it.embedding) }
                .sortedByDescending { it.second }
                .take(poolK)
        } else {
            emptyList()
        }
            
        // 2. Sparse Search (FTS5) - clean tokens to prevent SQLite syntax errors
        val cleanTokens = expandedQuery
            .replace(Regex("[^a-zA-Z0-9\\s]"), " ")
            .trim()
            .split(Regex("\\s+"))
            .filter { it.isNotBlank() && it.length > 1 }

        val sparseHits = if (cleanTokens.isNotEmpty()) {
            val ftsQuery = cleanTokens.joinToString(" OR ") { "$it*" }
            try {
                dao.searchFts(ftsQuery, poolK)
            } catch (e: Exception) {
                emptyList()
            }
        } else {
            emptyList()
        }
        
        // 3. RRF Fusion / Candidate Selection
        val fusedCandidates = if (denseHits.isNotEmpty() || sparseHits.isNotEmpty()) {
            performRrf(denseHits, sparseHits).take(poolK)
        } else {
            // Fallback: Word overlap or recent memories
            val queryWords = query.lowercase().split(Regex("[^a-zA-Z0-9]+")).filter { it.length > 2 }.toSet()
            if (queryWords.isNotEmpty()) {
                allMemories
                    .map { mem ->
                        val textWords = mem.text.lowercase().split(Regex("[^a-zA-Z0-9]+")).toSet()
                        val overlap = queryWords.intersect(textWords).size
                        mem to overlap
                    }
                    .filter { it.second > 0 }
                    .sortedByDescending { it.second }
                    .map { it.first }
                    .take(poolK)
                    .ifEmpty { allMemories.take(poolK) }
            } else {
                allMemories.take(poolK)
            }
        }
        
        // 4. Cross-Encoder Re-rank or Normalized Scoring
        return if (reranker != null) {
            fusedCandidates.map { record ->
                val score = reranker.rerank(query, record.text) // Original query, not expanded
                record to score
            }
            .sortedByDescending { it.second }
            .take(topK)
        } else {
            val queryWords = query.lowercase().split(Regex("[^a-zA-Z0-9]+")).filter { it.length > 2 }.toSet()
            fusedCandidates.mapIndexed { index, record ->
                val textWords = record.text.lowercase().split(Regex("[^a-zA-Z0-9]+")).toSet()
                val overlapRatio = if (queryWords.isNotEmpty()) {
                    queryWords.intersect(textWords).size.toFloat() / queryWords.size.toFloat()
                } else 0f
                val rankDecay = 1.0f / (1.0f + index * 0.15f)
                val score = (0.55f * rankDecay + 0.45f * overlapRatio).coerceIn(0.10f, 0.98f)
                record to score
            }.take(topK)
        }
    }

    private fun dotProduct(vec1: List<Float>, vec2: List<Float>): Float {
        if (vec1.size != vec2.size) return 0f
        var sum = 0f
        for (i in vec1.indices) {
            sum += vec1[i] * vec2[i]
        }
        return sum
    }

    private fun performRrf(
        denseHits: List<Pair<MemoryRecord, Float>>,
        sparseHits: List<MemoryRecord>
    ): List<MemoryRecord> {
        val rrfK = 60
        val scores = mutableMapOf<Long, Float>()
        val recordsMap = mutableMapOf<Long, MemoryRecord>()
        
        denseHits.forEachIndexed { index, pair ->
            val id = pair.first.id
            scores[id] = (scores[id] ?: 0f) + (1f / (rrfK + index + 1))
            recordsMap[id] = pair.first
        }
        
        sparseHits.forEachIndexed { index, record ->
            val id = record.id
            scores[id] = (scores[id] ?: 0f) + (1f / (rrfK + index + 1))
            recordsMap[id] = record
        }
        
        return scores.entries
            .sortedByDescending { it.value }
            .mapNotNull { recordsMap[it.key] }
    }
}
