package com.eykon.memory.ml.vision

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import com.eykon.memory.assistant.ModelManager
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.roundToInt

/**
 * YOLOE-11L (AGPL-3.0: allowed while the project is academic, docs/invariants/tooling.md) with its word
 * list fixed when it was exported to ONNX: "keys", "a wallet", "glasses", "earbuds", "a phone", "a pen".
 * The app takes only keys and earbuds from it (D-FINE names the rest): the split measured on the Pixel,
 * 2.3 s per frame, same scores as the laptop (docs/results/2026-10-14-detectors-open-vocabulary.md).
 * assets/yoloe_words.json is written by src/benchmarks/phone_detector_assets.py.
 */
object YoloeDetector {

    const val MODEL_FILE = "yoloe_11l_own.onnx"
    const val SIDE = 640
    const val MIN_CONF = 0.25f
    private const val PAD = 114
    private const val WORDS_ASSET = "yoloe_words.json"

    /** The plain names in the model's class order, and the ones the app takes from YOLOE. */
    class Words(val names: List<String>, val use: Set<String>)

    private val environment: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private var session: OrtSession? = null
    private var words: Words? = null

    fun modelFile(context: Context): File = File(ModelManager.getPreferredDirectory(context), MODEL_FILE)

    @Synchronized
    private fun session(context: Context): OrtSession = session ?: run {
        val file = modelFile(context)
        if (!file.exists()) throw IllegalStateException("the YOLOE model is missing: push $MODEL_FILE to ${file.parent}")
        environment.createSession(file.absolutePath, OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) }).also { session = it }
    }

    @Synchronized
    fun words(context: Context): Words = words ?: Json.parseToJsonElement(
        context.assets.open(WORDS_ASSET).bufferedReader().use { it.readText() },
    ).jsonObject.let { o ->
        Words(o["names"]!!.jsonArray.map { it.jsonPrimitive.content }, o["use"]!!.jsonArray.map { it.jsonPrimitive.content }.toSet())
    }.also { words = it }

    /** About 570 MB while loaded: let it go after a video. */
    @Synchronized
    fun close() {
        session?.close()
        session = null
    }

    /** Each word's best score on this picture, for every word in the list (the phone test compares these with the laptop). */
    fun bestScores(context: Context, bitmap: Bitmap): Map<String, Float> {
        val (rows, _) = run(context, bitmap)
        return words(context).names.withIndex().associate { (c, name) -> name to rows[4 + c].max() }
    }

    /** At most one detection per word the app takes from YOLOE: its surest box, when at least [minConf]. */
    fun detect(context: Context, bitmap: Bitmap, minConf: Float = MIN_CONF): List<Detection> {
        val (rows, fit) = run(context, bitmap)
        val words = words(context)
        return decode(rows, words.names, words.use, fit, bitmap.width, bitmap.height, minConf)
    }

    private fun run(context: Context, bitmap: Bitmap): Pair<Array<FloatArray>, Fit> {
        val ratio = minOf(SIDE / bitmap.width.toFloat(), SIDE / bitmap.height.toFloat())
        val w = (bitmap.width * ratio).roundToInt()
        val h = (bitmap.height * ratio).roundToInt()
        val scaled = if (w == bitmap.width && h == bitmap.height) bitmap else Bitmap.createScaledBitmap(bitmap, w, h, true)
        val pixels = IntArray(w * h)
        scaled.getPixels(pixels, 0, w, 0, 0, w, h)
        if (scaled !== bitmap) scaled.recycle()
        val fit = fit(w, h, ratio)
        val session = session(context)
        OnnxTensor.createTensor(environment, FloatBuffer.wrap(letterbox(pixels, w, h, fit)), longArrayOf(1, 3, SIDE.toLong(), SIDE.toLong())).use { tensor ->
            session.run(mapOf("images" to tensor), setOf("output0")).use { result ->
                @Suppress("UNCHECKED_CAST")
                return (result.get(0).value as Array<Array<FloatArray>>)[0] to fit
            }
        }
    }

    /** Where the picture sits in the square: Ultralytics' centred letterbox. */
    class Fit(val left: Int, val top: Int, val ratio: Float)

    internal fun fit(w: Int, h: Int, ratio: Float) =
        Fit(Math.round((SIDE - w) / 2f - 0.1f), Math.round((SIDE - h) / 2f - 0.1f), ratio)

    /** The picture ([w] x [h], already scaled) centred on a grey square; red, green, blue planes, 0 to 1. */
    internal fun letterbox(argb: IntArray, w: Int, h: Int, fit: Fit): FloatArray {
        val plane = SIDE * SIDE
        val out = FloatArray(3 * plane) { PAD / 255f }
        for (y in 0 until h) for (x in 0 until w) {
            val p = argb[y * w + x]
            val i = (y + fit.top) * SIDE + x + fit.left
            out[i] = ((p shr 16) and 0xFF) / 255f
            out[plane + i] = ((p shr 8) and 0xFF) / 255f
            out[2 * plane + i] = (p and 0xFF) / 255f
        }
        return out
    }

    /** Rows: centre x, centre y, width, height, one score per word, then mask values; one column per candidate box. */
    internal fun decode(rows: Array<FloatArray>, names: List<String>, use: Set<String>, fit: Fit, width: Int, height: Int, minConf: Float): List<Detection> =
        names.withIndex().filter { it.value in use }.mapNotNull { (c, name) ->
            val scores = rows[4 + c]
            val j = scores.indices.maxBy { scores[it] }
            if (scores[j] < minConf) return@mapNotNull null
            val (cx, cy, w, h) = listOf(rows[0][j], rows[1][j], rows[2][j], rows[3][j])
            fun x(v: Float) = ((v - fit.left) / fit.ratio).coerceIn(0f, width.toFloat())
            fun y(v: Float) = ((v - fit.top) / fit.ratio).coerceIn(0f, height.toFloat())
            Detection(name, scores[j], listOf(x(cx - w / 2), y(cy - h / 2), x(cx + w / 2), y(cy + h / 2)), "own")
        }.sortedByDescending { it.conf }
}
