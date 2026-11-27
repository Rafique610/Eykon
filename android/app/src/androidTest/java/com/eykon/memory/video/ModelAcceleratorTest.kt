package com.eykon.memory.video

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.os.Build
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.assistant.ModelManager
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.FloatBuffer
import java.nio.LongBuffer
import java.util.Locale
import kotlin.math.abs
import kotlin.math.max

/**
 * Hypothesis 7 (decision re-check, 26 Nov): every model timing so far is CPU only (4 threads), so "the phone is too slow" was
 * never checked against the accelerators ONNX Runtime Android offers: XNNPACK (a faster CPU kernel library) and NNAPI
 * (Android's route to the GPU / NPU; deprecated from Android 15 but still on our Android 13 Infinix). For each of the five
 * models: the app's setting, XNNPACK, NNAPI; median of 10 runs after 2 warm-ups, and the largest change in any output
 * against the app's setting on the same input. Measurement only, logcat tag EYKO_ACCEL; models from the app's model folder.
 * The same fixed input for every setting (speed does not depend on what a picture shows). Argument `-e runs 10`.
 */
@RunWith(AndroidJUnit4::class)
class ModelAcceleratorTest {

    private val tag = "EYKO_ACCEL"
    private val env = OrtEnvironment.getEnvironment()

    // file, input name, shape, the app's optimisation (D-FINE runs with it off, DfineDetector.kt)
    private val models = listOf(
        Spec("yolox_tiny.onnx", "images", longArrayOf(1, 3, 416, 416), OrtSession.SessionOptions.OptLevel.ALL_OPT, 255f),
        Spec("dfine_s_obj365.onnx", "pixel_values", longArrayOf(1, 3, 640, 640), OrtSession.SessionOptions.OptLevel.NO_OPT, 1f),
        Spec("yoloe_11l_own.onnx", "images", longArrayOf(1, 3, 640, 640), OrtSession.SessionOptions.OptLevel.ALL_OPT, 1f),
        Spec("mobileclip_s2_image.onnx", "image", longArrayOf(1, 3, 256, 256), OrtSession.SessionOptions.OptLevel.ALL_OPT, 1f),
        Spec("mobileclip_s2_text.onnx", "tokens", longArrayOf(1, 77), OrtSession.SessionOptions.OptLevel.ALL_OPT, 0f),
    )

    private class Spec(val file: String, val input: String, val shape: LongArray, val level: OrtSession.SessionOptions.OptLevel, val scale: Float)

    private fun input(s: Spec): OnnxTensor {
        val n = s.shape.fold(1L) { a, b -> a * b }.toInt()
        return if (s.scale == 0f) { // token ids: start, a few words, end, then padding (the CLIP tokenizer's shape)
            val ids = LongArray(n).also { it[0] = 49406; for (i in 1..6) it[i] = 320L + i * 37; it[7] = 49407 }
            OnnxTensor.createTensor(env, LongBuffer.wrap(ids), s.shape)
        } else { // a smooth fixed pattern in the model's value range
            val f = FloatArray(n) { i -> s.scale * (0.5f + 0.5f * kotlin.math.sin(i * 0.0007f).toFloat()) }
            OnnxTensor.createTensor(env, FloatBuffer.wrap(f), s.shape)
        }
    }

    private fun options(s: Spec, way: String): OrtSession.SessionOptions = OrtSession.SessionOptions().apply {
        setOptimizationLevel(s.level)
        when (way) {
            "app" -> setIntraOpNumThreads(4)
            "xnnpack" -> { setIntraOpNumThreads(1); addXnnpack(mapOf("intra_op_num_threads" to "4")) } // ORT's advice for XNNPACK
            "nnapi" -> { setIntraOpNumThreads(4); addNnapi() }
        }
    }

    private fun outputs(session: OrtSession, s: Spec, x: OnnxTensor): List<FloatArray> = session.run(mapOf(s.input to x)).use { r ->
        r.map { (it.value as OnnxTensor).floatBuffer.let { b -> FloatArray(b.remaining()).also { a -> b.get(a) } } }
    }

    @Test
    fun accelerators() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val runs = InstrumentationRegistry.getArguments().getString("runs")?.toInt() ?: 10
        val dir = ModelManager.getPreferredDirectory(context)
        Log.i(tag, "device ${Build.MANUFACTURER} ${Build.MODEL}, Android ${Build.VERSION.RELEASE}, models in $dir, $runs runs")
        for (s in models) {
            val file = File(dir, s.file)
            if (!file.exists()) { Log.i(tag, "${s.file}: missing, skipped"); continue }
            input(s).use { x ->
                var reference: List<FloatArray>? = null
                for (way in listOf("app", "xnnpack", "nnapi")) {
                    val line = runCatching {
                        val loadStart = System.nanoTime()
                        env.createSession(file.absolutePath, options(s, way)).use { session ->
                            val loadMs = (System.nanoTime() - loadStart) / 1e6
                            repeat(2) { session.run(mapOf(s.input to x)).close() }
                            val ms = DoubleArray(runs) {
                                val t = System.nanoTime(); session.run(mapOf(s.input to x)).close(); (System.nanoTime() - t) / 1e6
                            }.sorted()
                            val out = outputs(session, s, x)
                            if (way == "app") reference = out
                            val change = reference?.zip(out)?.maxOfOrNull { (a, b) -> a.indices.maxOfOrNull { abs(a[it] - b[it]) } ?: 0f } ?: 0f
                            "%s %s: load %.0f ms, median %.1f ms, fastest %.1f ms, largest output change vs app %.5f"
                                .format(Locale.ROOT, s.file, way, loadMs, ms[runs / 2], ms[0], max(0f, change))
                        }
                    }.getOrElse { "${s.file} $way: FAILED ${it.javaClass.simpleName}: ${it.message?.take(200)}" }
                    Log.i(tag, line)
                }
            }
        }
    }
}
