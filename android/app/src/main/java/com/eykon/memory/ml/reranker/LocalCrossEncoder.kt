package com.eykon.memory.ml.reranker

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import com.eykon.memory.ml.embedder.TokenizerHelper
import java.nio.LongBuffer

class LocalCrossEncoder(modelPath: String) {
    private val env = OrtEnvironment.getEnvironment()
    private val session: OrtSession

    init {
        session = env.createSession(modelPath, OrtSession.SessionOptions())
    }

    fun rerank(query: String, document: String): Float {
        // Tokenize query and document as [CLS] query [SEP] document [SEP]
        val queryTokens = TokenizerHelper.tokenize(query)
        val docTokens = TokenizerHelper.tokenize(document)
        
        // Truncate to fit model max length (e.g., 512)
        val maxLen = 512
        val availableDocLen = maxLen - queryTokens.size - 3 // 3 for CLS, SEP, SEP
        val actualDocTokens = if (docTokens.size > availableDocLen) {
            docTokens.take(availableDocLen.coerceAtLeast(0))
        } else {
            docTokens
        }
        
        // 101 = CLS, 102 = SEP for standard BERT/MiniLM
        val clsToken = 101
        val sepToken = 102
        
        val inputIds = mutableListOf(clsToken)
        inputIds.addAll(queryTokens)
        inputIds.add(sepToken)
        
        val tokenTypeIds = mutableListOf<Int>()
        repeat(inputIds.size) { tokenTypeIds.add(0) }
        
        inputIds.addAll(actualDocTokens)
        inputIds.add(sepToken)
        
        repeat(actualDocTokens.size + 1) { tokenTypeIds.add(1) }
        
        val attentionMask = LongArray(inputIds.size) { 1L }
        val inputIdsArray = LongArray(inputIds.size) { inputIds[it].toLong() }
        val tokenTypeIdsArray = LongArray(tokenTypeIds.size) { tokenTypeIds[it].toLong() }
        
        val shape = longArrayOf(1, inputIds.size.toLong())

        val inputTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(inputIdsArray), shape)
        val maskTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(attentionMask), shape)
        val typeTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(tokenTypeIdsArray), shape)

        val inputs = mapOf(
            "input_ids" to inputTensor,
            "attention_mask" to maskTensor,
            "token_type_ids" to typeTensor
        )

        return try {
            val results = session.run(inputs)
            @Suppress("UNCHECKED_CAST")
            val output = results.get(0).value as Array<FloatArray>
            // Cross encoder usually returns logits for class 0 (or class 1)
            output[0][0]
        } catch (e: Exception) {
            e.printStackTrace()
            0f
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
