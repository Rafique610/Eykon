package com.eykon.memory.ml.embedder

object TokenizerHelper {
    /**
     * Splits text into overlapping chunks simulating Phase 1 logic:
     * - Target ~256 tokens
     * - Overlap of 30-50 tokens
     * - Max 400 tokens ceiling
     * 
     * Note: Since we lack the exact ONNX WordPiece tokenizer right now, 
     * we approximate using words (1 word ≈ 1.3 tokens).
     * ~195 words target, ~30 words overlap, ~300 words max.
     */
    fun chunkText(text: String): List<String> {
        val words = text.split(Regex("\\s+"))
        val chunks = mutableListOf<String>()
        
        val targetWords = 195 // ~256 tokens
        val overlapWords = 30 // ~40 tokens
        
        if (words.size <= targetWords) return listOf(text)

        var i = 0
        while (i < words.size) {
            val end = (i + targetWords).coerceAtMost(words.size)
            val chunk = words.subList(i, end).joinToString(" ")
            chunks.add(chunk)
            
            if (end == words.size) break
            // Move forward by target size minus the overlap
            i += (targetWords - overlapWords)
        }

        return chunks
    }

    /**
     * Placeholder WordPiece tokenizer.
     * For full on-device ONNX inference, this will either use onnxruntime-extensions
     * or a custom WordPiece Kotlin implementation when the vocab is provided.
     */
    fun tokenize(text: String): List<Int> {
        // Dummy tokenization mapping chars to ASCII for shape testing
        return text.take(512).map { it.code }
    }
}
