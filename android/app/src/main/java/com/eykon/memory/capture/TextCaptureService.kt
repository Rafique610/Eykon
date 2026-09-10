package com.eykon.memory.capture

import com.eykon.memory.data.MemoryRecord
import com.eykon.memory.ml.embedder.LocalEmbedder
import com.eykon.memory.ml.embedder.TokenizerHelper
import java.time.Instant

/**
 * Validates raw text input and produces MemoryRecords ready for storage.
 * Updated in Step 04 to support chunking and real embeddings.
 */
object TextCaptureService {

    var embedder: LocalEmbedder? = null

    fun createMemoriesFromText(text: String): List<MemoryRecord> {
        val cleaned = text.trim()
        require(cleaned.isNotEmpty()) { "Memory text cannot be empty or whitespace only" }

        val chunks = TokenizerHelper.chunkText(cleaned)
        val timestamp = Instant.now().toString()

        return chunks.mapIndexed { index, chunkText ->
            val embedding = embedder?.embed(chunkText) ?: emptyList()
            
            MemoryRecord(
                text = chunkText,
                embedding = embedding,
                timestamp = timestamp,
                sourceType = "text",
                metadata = """{"chunk_index": $index, "total_chunks": ${chunks.size}, "token_count": 0}"""
            )
        }
    }
}
