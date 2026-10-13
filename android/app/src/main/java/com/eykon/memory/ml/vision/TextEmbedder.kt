package com.eykon.memory.ml.vision

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import com.eykon.memory.assistant.ModelManager
import java.io.File
import java.nio.LongBuffer

/**
 * MobileCLIP-S2's text encoder (ONNX, exported by src/benchmarks/export_clip_text.py): a
 * phrase in, 512 numbers of length 1 out, in the same space as [ImageEmbedder]'s vectors. A
 * phrase and a picture that go together give vectors that point the same way.
 *
 * Same weights and licence as the image encoder (Apple Machine Learning Research Model License,
 * research and academic use only). The file is pushed to the phone's models folder by hand.
 */
object TextEmbedder {

    const val MODEL_FILE = "mobileclip_s2_text.onnx"
    private const val MERGES_ASSET = "clip_bpe_merges.txt"

    private val environment: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private var session: OrtSession? = null
    private var tokenizer: ClipTokenizer? = null

    fun modelFile(context: Context): File = File(ModelManager.getPreferredDirectory(context), MODEL_FILE)

    @Synchronized
    private fun session(context: Context): OrtSession = session ?: run {
        val file = modelFile(context)
        if (!file.exists()) throw IllegalStateException("the text model is missing: push $MODEL_FILE to ${file.parent}")
        val options = OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) }
        environment.createSession(file.absolutePath, options).also { session = it }
    }

    @Synchronized
    private fun tokenizer(context: Context): ClipTokenizer = tokenizer ?: run {
        val merges = context.assets.open(MERGES_ASSET).bufferedReader().useLines { lines -> lines.filter { it.isNotEmpty() }.toList() }
        ClipTokenizer(merges).also { tokenizer = it }
    }

    fun embed(context: Context, text: String): FloatArray {
        val tokens = tokenizer(context).encode(text)
        OnnxTensor.createTensor(environment, LongBuffer.wrap(tokens), longArrayOf(1, ClipTokenizer.LENGTH.toLong())).use { input ->
            session(context).run(mapOf("tokens" to input)).use { result ->
                @Suppress("UNCHECKED_CAST")
                return (result.get(0).value as Array<FloatArray>)[0]
            }
        }
    }
}
