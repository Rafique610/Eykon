package com.eykon.memory.ml.vision

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import com.eykon.memory.assistant.ModelManager
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import java.io.File
import java.nio.FloatBuffer
import java.nio.LongBuffer
import kotlin.math.exp
import kotlin.math.max

/**
 * OWLv2 base (Apache-2.0), the 8-bit ONNX file, asked for the user's own small things by name
 * ("keys", "earbuds": what D-FINE never named on our clips). About 13 s per frame on the Pixel, so the
 * stage "small_objects" runs it only on the frames MobileCLIP picks (card EYKO-32). The phrases come
 * as tokens in assets/owl_queries.json, written by src/benchmarks/phone_detector_assets.py.
 */
object OwlDetector {

    const val MODEL_FILE = "owlv2_q8.onnx"
    const val SIDE = 960
    const val MIN_CONF = 0.3f
    private const val QUERIES_ASSET = "owl_queries.json"
    private val MEAN = floatArrayOf(0.48145466f, 0.4578275f, 0.40821073f)
    private val STD = floatArrayOf(0.26862954f, 0.26130258f, 0.27577711f)

    private val environment: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private var session: OrtSession? = null
    private var queries: JsonObject? = null

    fun modelFile(context: Context): File = File(ModelManager.getPreferredDirectory(context), MODEL_FILE)

    @Synchronized
    private fun session(context: Context): OrtSession = session ?: run {
        val file = modelFile(context)
        if (!file.exists()) throw IllegalStateException("the OWLv2 model is missing: push $MODEL_FILE to ${file.parent}")
        environment.createSession(file.absolutePath, OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) }).also { session = it }
    }

    /** The phrases, their tokens, and the MobileCLIP vectors that pick frames. */
    @Synchronized
    fun queries(context: Context): JsonObject = queries ?: Json.parseToJsonElement(
        context.assets.open(QUERIES_ASSET).bufferedReader().use { it.readText() },
    ).jsonObject.also { queries = it }

    fun phrases(context: Context): List<String> = queries(context)["phrases"]!!.jsonArray.map { it.jsonPrimitive.content }

    fun pickVectors(context: Context): List<FloatArray> =
        queries(context)["pick_vectors"]!!.jsonArray.map { v -> v.jsonArray.map { it.jsonPrimitive.float }.toFloatArray() }

    /** The model takes about 150 MB and much more while running: let it go after a video. */
    @Synchronized
    fun close() {
        session?.close()
        session = null
    }

    /** At most one detection per phrase: its surest box, when at least [minConf]. Source "owl". */
    fun detect(context: Context, bitmap: Bitmap, minConf: Float = MIN_CONF): List<Detection> {
        val pixels = IntArray(bitmap.width * bitmap.height)
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        val square = max(bitmap.width, bitmap.height)
        val input = ImagePrep.rgbPlanes(pixels, bitmap.width, bitmap.height, SIDE, padTo = square)
        val plane = SIDE * SIDE
        for (c in 0..2) for (i in 0 until plane) input[c * plane + i] = (input[c * plane + i] - MEAN[c]) / STD[c]

        val q = queries(context)
        val ids = q["input_ids"]!!.jsonArray.flatMap { row -> row.jsonArray.map { it.jsonPrimitive.long } }.toLongArray()
        val mask = q["attention_mask"]!!.jsonArray.flatMap { row -> row.jsonArray.map { it.jsonPrimitive.long } }.toLongArray()
        val shape = longArrayOf(q["input_ids"]!!.jsonArray.size.toLong(), (ids.size / q["input_ids"]!!.jsonArray.size).toLong())
        val session = session(context)
        OnnxTensor.createTensor(environment, LongBuffer.wrap(ids), shape).use { idsTensor ->
            OnnxTensor.createTensor(environment, LongBuffer.wrap(mask), shape).use { maskTensor ->
                OnnxTensor.createTensor(environment, FloatBuffer.wrap(input), longArrayOf(1, 3, SIDE.toLong(), SIDE.toLong())).use { pixelTensor ->
                    val feed = mapOf("input_ids" to idsTensor, "attention_mask" to maskTensor, "pixel_values" to pixelTensor)
                    session.run(feed, setOf("logits", "pred_boxes")).use { result ->
                        @Suppress("UNCHECKED_CAST")
                        val logits = (result.get("logits").get().value as Array<Array<FloatArray>>)[0]
                        @Suppress("UNCHECKED_CAST")
                        val boxes = (result.get("pred_boxes").get().value as Array<Array<FloatArray>>)[0]
                        return decode(logits, boxes, phrases(context), square, bitmap.width, bitmap.height, minConf)
                    }
                }
            }
        }
    }

    /** Per phrase, the box with the highest score. Boxes are centre and size, 0 to 1 of the padded square. */
    internal fun decode(logits: Array<FloatArray>, boxes: Array<FloatArray>, phrases: List<String>, square: Int, width: Int, height: Int, minConf: Float): List<Detection> =
        phrases.indices.mapNotNull { p ->
            val b = logits.indices.maxBy { logits[it][p] }
            val conf = (1 / (1 + exp(-logits[b][p].toDouble()))).toFloat()
            if (conf < minConf) return@mapNotNull null
            val (cx, cy, w, h) = boxes[b].toList()
            val box = listOf((cx - w / 2) * square, (cy - h / 2) * square, (cx + w / 2) * square, (cy + h / 2) * square)
            Detection(phrases[p], conf, listOf(box[0].coerceIn(0f, width.toFloat()), box[1].coerceIn(0f, height.toFloat()),
                box[2].coerceIn(0f, width.toFloat()), box[3].coerceIn(0f, height.toFloat())), "owl")
        }
}
