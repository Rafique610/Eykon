package com.eykon.memory.ml.vision

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import com.eykon.memory.assistant.ModelManager
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.exp

/**
 * D-FINE S trained on Objects365 (Apache-2.0), the onnx-community ONNX file, on the CPU. It knows
 * 365 everyday things, among them wallet, glasses and pen (card EYKO-32; measured in
 * docs/results/2026-10-14-detectors-open-vocabulary.md). Runs next to YOLOX-Tiny in Option A.
 * src/benchmarks/phone_detector_assets.py writes the class names and the laptop answer the phone test checks.
 */
object DfineDetector {

    const val MODEL_FILE = "dfine_s_obj365.onnx"
    const val SIDE = 640
    const val MIN_CONF = 0.5f
    private const val LABELS_ASSET = "dfine_labels.json"

    private val environment: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private var session: OrtSession? = null
    private var labels: List<String>? = null

    fun modelFile(context: Context): File = File(ModelManager.getPreferredDirectory(context), MODEL_FILE)

    @Synchronized
    private fun session(context: Context): OrtSession = session ?: run {
        val file = modelFile(context)
        if (!file.exists()) throw IllegalStateException("the D-FINE model is missing: push $MODEL_FILE to ${file.parent}")
        // onnxruntime-android 1.18 fails on this model's ScatterND node when the graph is optimised
        val options = OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(4)
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.NO_OPT)
        }
        environment.createSession(file.absolutePath, options).also { session = it }
    }

    @Synchronized
    private fun labels(context: Context): List<String> = labels ?: Json.parseToJsonElement(
        context.assets.open(LABELS_ASSET).bufferedReader().use { it.readText() },
    ).jsonArray.map { it.jsonPrimitive.content }.also { labels = it }

    /** Objects365 names in plain words: the first of "Wallet/Purse", lower case. */
    internal fun plain(name: String): String = name.substringBefore('/').trim().lowercase()

    /** Everything found with confidence of at least [minConf], surest first, with plain names. */
    fun detect(context: Context, bitmap: Bitmap, minConf: Float = MIN_CONF): List<Detection> {
        val pixels = IntArray(bitmap.width * bitmap.height)
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        val input = ImagePrep.rgbPlanes(pixels, bitmap.width, bitmap.height, SIDE, wholeValues = true)
        val session = session(context)
        OnnxTensor.createTensor(environment, FloatBuffer.wrap(input), longArrayOf(1, 3, SIDE.toLong(), SIDE.toLong())).use { tensor ->
            session.run(mapOf("pixel_values" to tensor), setOf("logits", "pred_boxes")).use { result ->
                @Suppress("UNCHECKED_CAST")
                val logits = (result.get("logits").get().value as Array<Array<FloatArray>>)[0]
                @Suppress("UNCHECKED_CAST")
                val boxes = (result.get("pred_boxes").get().value as Array<Array<FloatArray>>)[0]
                return decode(logits, boxes, labels(context), bitmap.width, bitmap.height, minConf)
            }
        }
    }

    /** One answer per query box: its likeliest class, kept when sure enough. Boxes are centre and size, 0 to 1. */
    internal fun decode(logits: Array<FloatArray>, boxes: Array<FloatArray>, names: List<String>, width: Int, height: Int, minConf: Float): List<Detection> =
        logits.indices.mapNotNull { q ->
            val c = logits[q].indices.maxBy { logits[q][it] }
            val conf = (1 / (1 + exp(-logits[q][c].toDouble()))).toFloat()
            if (conf < minConf) return@mapNotNull null
            val (cx, cy, w, h) = boxes[q].toList()
            Detection(plain(names[c]), conf, listOf((cx - w / 2) * width, (cy - h / 2) * height, (cx + w / 2) * width, (cy + h / 2) * height))
        }.sortedByDescending { it.conf }
}
