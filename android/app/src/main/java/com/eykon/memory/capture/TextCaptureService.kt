package com.eykon.memory.capture

import com.eykon.memory.data.MemoryRecord
import java.time.Instant

/**
 * Validates raw text input and produces a MemoryRecord ready for storage.
 * In Step 02, embeddings are placeholder empty lists; real embeddings arrive in Step 04.
 */
object TextCaptureService {

    fun createMemoryFromText(text: String): MemoryRecord {
        val cleaned = text.trim()
        require(cleaned.isNotEmpty()) { "Memory text cannot be empty or whitespace only" }

        return MemoryRecord(
            text = cleaned,
            embedding = emptyList(), // Placeholder; Step 04 generates on-device embeddings
            timestamp = Instant.now().toString(),
            sourceType = "text",
            metadata = """{"chunk_index": 0, "total_chunks": 1, "token_count": 0}"""
        )
    }
}
