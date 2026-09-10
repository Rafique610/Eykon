package com.eykon.memory.retrieval

import com.eykon.memory.data.MemoryDao
import com.eykon.memory.data.MemoryRecord
import com.eykon.memory.ml.embedder.LocalEmbedder
import com.eykon.memory.ml.reranker.LocalCrossEncoder
import kotlin.math.sqrt

class SearchService(
    private val dao: MemoryDao,
    private val embedder: LocalEmbedder,
    private val reranker: LocalCrossEncoder
) {
    suspend fun search(query: String, poolK: Int = 20, topK: Int = 5): List<Pair<MemoryRecord, Float>> {
        val expandedQuery = QueryExpander.expand(query)
        
        // 1. Dense Search
        val queryVector = embedder.embed(expandedQuery)
        val allMemories = dao.getAll()
        val denseHits = allMemories
            .filter { it.hasEmbedding }
            .map { it to dotProduct(queryVector, it.embedding) }
            .sortedByDescending { it.second }
            .take(poolK)
            
        // 2. Sparse Search (FTS5)
        val ftsQuery = expandedQuery.split(Regex("\\s+")).joinToString(" OR ") { "$it*" }
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
