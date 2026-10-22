package com.eykon.memory.ml.embedder

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.LongBuffer
import kotlin.math.sqrt

class LocalEmbedder(modelPath: String) {
    private val env = OrtEnvironment.getEnvironment()
    private val session: OrtSession

    init {
        session = env.createSession(modelPath, OrtSession.SessionOptions())
    }

    fun embed(text: String): List<Float> {
        // Tokenize text
        val tokens = TokenizerHelper.tokenize(text)
        if (tokens.isEmpty()) return emptyList()
        
        val inputIds = LongArray(tokens.size) { tokens[it].toLong() }
        val attentionMask = LongArray(tokens.size) { 1L }
        val tokenTypeIds = LongArray(tokens.size) { 0L }

        val shape = longArrayOf(1, tokens.size.toLong())

        val inputTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(inputIds), shape)
        val maskTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(attentionMask), shape)
        val typeTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(tokenTypeIds), shape)

        val inputs = mapOf(
            "input_ids" to inputTensor,
            "attention_mask" to maskTensor,
            "token_type_ids" to typeTensor
        )

        return try {
            val results = session.run(inputs)
            val embeddingsObj = results.get(0).value
            
            // Extract the embeddings. The output shape depends on the exact model.
            // bge-small usually outputs [batch, seq_length, hidden_size]
            @Suppress("UNCHECKED_CAST")
            val embeddings = embeddingsObj as Array<Array<FloatArray>>
            
            // Mean pooling
            val hiddenSize = embeddings[0][0].size
            val pooled = FloatArray(hiddenSize)
            var validTokens = 0
            for (i in tokens.indices) {
                if (attentionMask[i] == 1L) {
                    validTokens++
                    for (j in 0 until hiddenSize) {
                        pooled[j] += embeddings[0][i][j]
                    }
                }
            }
            for (j in 0 until hiddenSize) {
                pooled[j] /= validTokens.toFloat()
            }
            
            // Normalize
            var sumSq = 0f
            for (f in pooled) {
                sumSq += f * f
            }
            val norm = sqrt(sumSq).toFloat()
            
            pooled.map { if (norm > 0) it / norm else it }
        } finally {
            inputTensor.close()
            maskTensor.close()
            typeTensor.close()
        }
    }

    fun close() {
        session.close()
        env.close()
    }
}
