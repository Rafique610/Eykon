package com.eykon.memory.ml.vision

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import com.eykon.memory.assistant.ModelManager
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * MobileCLIP-S2's image encoder (ONNX, exported by src/benchmarks/export_clip.py): a picture in,
 * 512 numbers of length 1 out. Two pictures that show the same thing give nearly the same numbers.
 *
 * The weights are Apple's, under the Apple Machine Learning Research Model License: research and
 * academic use only. The file is pushed to the phone's models folder by hand and is never part of
 * the app package.
 */
object ImageEmbedder {

    const val MODEL_FILE = "mobileclip_s2_image.onnx"
    const val DIMENSIONS = 512
    private const val SIDE = 256

    private val environment: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private var session: OrtSession? = null

    fun modelFile(context: Context): File = File(ModelManager.getPreferredDirectory(context), MODEL_FILE)

    @Synchronized
    private fun session(context: Context): OrtSession = session ?: run {
        val file = modelFile(context)
        if (!file.exists()) throw IllegalStateException("the image model is missing: push $MODEL_FILE to ${file.parent}")
        val options = OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) } // CPU only, as measured
        environment.createSession(file.absolutePath, options).also { session = it }
    }

    fun embed(context: Context, file: File): FloatArray {
        val bitmap = BitmapFactory.decodeFile(file.absolutePath) ?: throw IllegalStateException("picture ${file.name} cannot be read")
        return embed(context, bitmap).also { bitmap.recycle() }
    }

    fun embed(context: Context, bitmap: Bitmap): FloatArray {
        OnnxTensor.createTensor(environment, FloatBuffer.wrap(preprocess(bitmap)), longArrayOf(1, 3, SIDE.toLong(), SIDE.toLong())).use { input ->
            session(context).run(mapOf("image" to input)).use { result ->
                @Suppress("UNCHECKED_CAST")
                return (result.get(0).value as Array<FloatArray>)[0]
            }
        }
    }

    /**
     * What the model was trained with: shorter side to 256, the middle 256 x 256 square,
     * colours as 0 to 1, laid out red plane, green plane, blue plane.
     */
    private fun preprocess(bitmap: Bitmap): FloatArray {
        val scale = SIDE / minOf(bitmap.width, bitmap.height).toDouble()
        val width = max(SIDE, (bitmap.width * scale).roundToInt())
        val height = max(SIDE, (bitmap.height * scale).roundToInt())
        val scaled = Bitmap.createScaledBitmap(bitmap, width, height, true)
        val pixels = IntArray(SIDE * SIDE)
        scaled.getPixels(pixels, 0, SIDE, (width - SIDE) / 2, (height - SIDE) / 2, SIDE, SIDE)
        if (scaled !== bitmap) scaled.recycle()
        val plane = SIDE * SIDE
        val out = FloatArray(3 * plane)
        for (i in 0 until plane) {
            val p = pixels[i]
            out[i] = ((p shr 16) and 0xFF) / 255f
            out[plane + i] = ((p shr 8) and 0xFF) / 255f
            out[2 * plane + i] = (p and 0xFF) / 255f
        }
        return out
    }
}
