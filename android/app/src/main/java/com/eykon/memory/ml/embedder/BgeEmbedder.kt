package com.eykon.memory.ml.embedder

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import com.eykon.memory.assistant.ModelManager
import java.io.File
import java.nio.LongBuffer
import kotlin.math.sqrt

/**
 * BAAI/bge-small-en-v1.5 (MIT), the Phase 1 text embedder, as the ONNX file from its own
 * repository: a sentence in, 384 numbers of length 1 out. Sentences that mean the same give
 * vectors that point the same way. The file is fetched with `task export-bge` and pushed to
 * the phone's models folder; the phone test compares its vectors with the laptop's.
 */
object BgeEmbedder {

    const val MODEL_FILE = "bge_small_en_v1.5.onnx"
    const val DIMENSIONS = 384
    private const val VOCAB_ASSET = "bge_vocab.txt"

    private val environment: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private var session: OrtSession? = null
    private var tokenizer: WordPieceTokenizer? = null

    fun modelFile(context: Context): File = File(ModelManager.getPreferredDirectory(context), MODEL_FILE)

    @Synchronized
    private fun session(context: Context): OrtSession = session ?: run {
        val file = modelFile(context)
        if (!file.exists()) throw IllegalStateException("the text embedder is missing: push $MODEL_FILE to ${file.parent}")
        val options = OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) }
        environment.createSession(file.absolutePath, options).also { session = it }
    }

    @Synchronized
    private fun tokenizer(context: Context): WordPieceTokenizer = tokenizer ?: run {
        WordPieceTokenizer(context.assets.open(VOCAB_ASSET).bufferedReader().readLines()).also { tokenizer = it }
    }

    fun embed(context: Context, text: String): FloatArray {
        val tokens = tokenizer(context).encode(text)
        val shape = longArrayOf(1, tokens.size.toLong())
        OnnxTensor.createTensor(environment, LongBuffer.wrap(tokens), shape).use { ids ->
            OnnxTensor.createTensor(environment, LongBuffer.wrap(LongArray(tokens.size) { 1 }), shape).use { mask ->
                OnnxTensor.createTensor(environment, LongBuffer.wrap(LongArray(tokens.size)), shape).use { types ->
                    session(context).run(mapOf("input_ids" to ids, "attention_mask" to mask, "token_type_ids" to types)).use { result ->
                        // The model answers once per token; the first one (the start marker) stands for the sentence.
                        @Suppress("UNCHECKED_CAST")
                        val first = (result.get(0).value as Array<Array<FloatArray>>)[0][0]
                        val length = sqrt(first.sumOf { it.toDouble() * it }).toFloat()
                        return FloatArray(first.size) { first[it] / length }
                    }
                }
            }
        }
    }
}
