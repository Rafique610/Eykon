package com.eykon.memory.assistant

/**
 * Generation hyperparameters matching current Phase 1 configuration.
 */
data class GenerationParams(
    val temperature: Float = 0.3f,
    val maxOutputTokens: Int = 256,
    val topK: Int = 40,
    val topP: Float = 0.95f
)
