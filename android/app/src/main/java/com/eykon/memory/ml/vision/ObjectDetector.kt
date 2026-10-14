package com.eykon.memory.ml.vision

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import com.eykon.memory.assistant.ModelManager
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.exp
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min

/**
 * One thing a detector found. [box] is left, top, right, bottom in the picture's own pixels.
 * [source] is "detector" (YOLOX-Tiny or D-FINE, every kept frame) or "owl" (OWLv2, picked frames only).
 */
data class Detection(val label: String, val conf: Float, val box: List<Float>, val source: String = "detector")

/**
 * YOLOX-Tiny (Apache-2.0), the official ONNX file, run with ONNX Runtime on the CPU. It knows the
 * 80 everyday COCO things (person, laptop, cup, chair ...), not small personal objects like keys.
 *
 * The three steps follow the official demo (demo/ONNXRuntime/onnx_inference.py in
 * github.com/Megvii-BaseDetection/YOLOX); src/benchmarks/perception_golden.py is the same maths
 * on the laptop, and the phone test compares the two.
 */
object ObjectDetector {

    const val MODEL_FILE = "yolox_tiny.onnx"
    const val SIDE = 416
    const val NMS_IOU = 0.45f
    private const val PAD = 114f
    private val STRIDES = intArrayOf(8, 16, 32)

    val LABELS: List<String> = (
        "person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter," +
            "bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee," +
            "skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass," +
            "cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch," +
            "potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink," +
            "refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush"
        ).split(",")

    private val environment: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private var session: OrtSession? = null
    private var modelName = MODEL_FILE

    /** Measurements swap in another official YOLOX file with the same 416 x 416 input (for example yolox_nano.onnx). */
    @Synchronized
    fun useModel(name: String) {
        session?.close()
        session = null
        modelName = name
    }

    fun modelFile(context: Context): File = File(ModelManager.getPreferredDirectory(context), modelName)

    @Synchronized
    private fun session(context: Context): OrtSession = session ?: run {
        val file = modelFile(context)
        if (!file.exists()) throw IllegalStateException("the detector model is missing: push $modelName to ${file.parent}")
        val options = OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) }
        environment.createSession(file.absolutePath, options).also { session = it }
    }

    /** Everything found with confidence of at least [minConf], surest first. */
    fun detect(context: Context, bitmap: Bitmap, minConf: Float): List<Detection> {
        val pixels = IntArray(bitmap.width * bitmap.height)
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        val (input, ratio) = letterbox(pixels, bitmap.width, bitmap.height)
        val session = session(context)
        OnnxTensor.createTensor(environment, FloatBuffer.wrap(input), longArrayOf(1, 3, SIDE.toLong(), SIDE.toLong())).use { tensor ->
            session.run(mapOf(session.inputNames.first() to tensor)).use { result ->
                @Suppress("UNCHECKED_CAST")
                val rows = (result.get(0).value as Array<Array<FloatArray>>)[0]
                return nms(decode(rows, ratio, minConf))
            }
        }
    }

    /**
     * Step 1. Shrink the picture to fit [SIDE] x [SIDE], put it top-left, fill the rest with grey.
     * Colours stay 0 to 255 and are laid out blue plane, green plane, red plane, as the model was
     * trained. The shrink is the same two-by-two blend OpenCV's INTER_LINEAR does.
     */
    internal fun letterbox(argb: IntArray, width: Int, height: Int): Pair<FloatArray, Float> {
        val ratio = min(SIDE / height.toDouble(), SIDE / width.toDouble())
        val newWidth = (width * ratio).toInt()
        val newHeight = (height * ratio).toInt()
        val plane = SIDE * SIDE
        val out = FloatArray(3 * plane) { PAD }
        val scaleX = width / newWidth.toDouble()
        val scaleY = height / newHeight.toDouble()
        for (y in 0 until newHeight) {
            val fy = max(0.0, (y + 0.5) * scaleY - 0.5)
            val y0 = min(floor(fy).toInt(), height - 1)
            val y1 = min(y0 + 1, height - 1)
            val wy = (fy - y0).toFloat()
            for (x in 0 until newWidth) {
                val fx = max(0.0, (x + 0.5) * scaleX - 0.5)
                val x0 = min(floor(fx).toInt(), width - 1)
                val x1 = min(x0 + 1, width - 1)
                val wx = (fx - x0).toFloat()
                val a = argb[y0 * width + x0]
                val b = argb[y0 * width + x1]
                val c = argb[y1 * width + x0]
                val d = argb[y1 * width + x1]
                val i = y * SIDE + x
                for (channel in 0..2) { // 0 blue, 1 green, 2 red
                    val shift = channel * 8
                    val top = ((a shr shift) and 0xFF) * (1 - wx) + ((b shr shift) and 0xFF) * wx
                    val bottom = ((c shr shift) and 0xFF) * (1 - wx) + ((d shr shift) and 0xFF) * wx
                    out[channel * plane + i] = Math.round(top * (1 - wy) + bottom * wy).toFloat()
                }
            }
        }
        return out to ratio.toFloat()
    }

    /**
     * Step 2. The model answers once per grid cell, at three grid sizes. Each row is the box's
     * centre and size relative to its cell, how sure the model is that something is there, and a
     * score per class. This turns the rows that are sure enough into boxes in the picture's pixels.
     */
    internal fun decode(rows: Array<FloatArray>, ratio: Float, minConf: Float): List<Detection> {
        val found = ArrayList<Detection>()
        var i = 0
        for (stride in STRIDES) {
            val cells = SIDE / stride
            for (gridY in 0 until cells) {
                for (gridX in 0 until cells) {
                    val row = rows[i++]
                    var best = 5
                    for (k in 6 until row.size) if (row[k] > row[best]) best = k
                    val conf = row[4] * row[best]
                    if (conf < minConf) continue
                    val centreX = (row[0] + gridX) * stride
                    val centreY = (row[1] + gridY) * stride
                    val w = exp(row[2]) * stride
                    val h = exp(row[3]) * stride
                    found.add(
                        Detection(
                            LABELS[best - 5], conf,
                            listOf((centreX - w / 2) / ratio, (centreY - h / 2) / ratio, (centreX + w / 2) / ratio, (centreY + h / 2) / ratio),
                        ),
                    )
                }
            }
        }
        return found
    }

    /** Step 3. Surest first; a box that overlaps an already kept one by more than [NMS_IOU] is the same thing seen twice. */
    internal fun nms(found: List<Detection>): List<Detection> {
        val kept = ArrayList<Detection>()
        for (candidate in found.sortedByDescending { it.conf }) {
            if (kept.all { overlap(it.box, candidate.box) <= NMS_IOU }) kept.add(candidate)
        }
        return kept
    }

    /** Shared area over combined area, with the demo's "+1" pixel convention. */
    internal fun overlap(a: List<Float>, b: List<Float>): Float {
        val w = max(0f, min(a[2], b[2]) - max(a[0], b[0]) + 1)
        val h = max(0f, min(a[3], b[3]) - max(a[1], b[1]) + 1)
        val shared = w * h
        return shared / (area(a) + area(b) - shared)
    }

    private fun area(box: List<Float>) = (box[2] - box[0] + 1) * (box[3] - box[1] + 1)
}
