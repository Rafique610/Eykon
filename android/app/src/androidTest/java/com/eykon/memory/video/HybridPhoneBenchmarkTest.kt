package com.eykon.memory.video

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.os.Build
import android.os.Debug
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.exp

/**
 * Card EYKO-32, the mixed detectors on the phone: D-FINE S (Objects365) and the 8-bit OWLv2 on all 50
 * own frames, each frame already turned into the models' input on the laptop. Writes each model's best
 * score per thing and its time per frame; `task hybrid-phone -- score` then scores every way of
 * picking frames. Only the model runs are timed. Not part of the app; skipped when the files are missing.
 *
 *   adb push D:/eykon-cache/bench/detectors/hybrid_phone/. /sdcard/Android/data/com.eykon.memory/files/hybrid_phone/
 *   adb shell am instrument -w -e class com.eykon.memory.video.HybridPhoneBenchmarkTest \
 *       com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
 *   adb pull /sdcard/Android/data/com.eykon.memory/files/hybrid_phone_result.json
 * `-e dfine_opt none` turns off graph optimisation for D-FINE (onnxruntime-android 1.18 fails on its
 * ScatterND node otherwise); `-e frames 2` runs only the first frames for a quick check.
 */
@RunWith(AndroidJUnit4::class)
class HybridPhoneBenchmarkTest {

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val env = OrtEnvironment.getEnvironment()

    private fun bytes(file: File): ByteBuffer = ByteBuffer.wrap(file.readBytes()).order(ByteOrder.LITTLE_ENDIAN)

    private fun shape(json: JsonElement): LongArray = json.jsonArray.map { it.jsonPrimitive.int.toLong() }.toLongArray()

    /** Highest sigmoid score over all boxes of any class listed for each thing. Logits: boxes x classes. */
    private fun bestPerThing(logits: Array<FloatArray>, lists: JsonObject): JsonObject = buildJsonObject {
        for ((thing, idx) in lists) {
            val classes = idx.jsonArray.map { it.jsonPrimitive.int }
            if (classes.isEmpty()) continue
            val top = logits.maxOf { box -> classes.maxOf { box[it] } }
            put(thing, Math.round(1000.0 / (1 + exp(-top.toDouble()))) / 1000.0)
        }
    }

    private fun timed(block: () -> Array<FloatArray>): Pair<Array<FloatArray>, Double> {
        val start = System.nanoTime()
        val out = block()
        return out to (System.nanoTime() - start) / 1e6
    }

    @Suppress("UNCHECKED_CAST")
    private fun logits(session: OrtSession, inputs: Map<String, OnnxTensor>): Array<FloatArray> =
        session.run(inputs, setOf("logits")).use { (it[0].value as Array<Array<FloatArray>>)[0] }

    @Test
    fun runBothModelsOnEveryFrame() {
        val dir = File(context.getExternalFilesDir(null), "hybrid_phone")
        assumeTrue("no hybrid_phone files on this phone", File(dir, "manifest.json").exists())
        val manifest = Json.parseToJsonElement(File(dir, "manifest.json").readText()).jsonObject
        val dfine = manifest["dfine"]!!.jsonObject
        val owl = manifest["owl"]!!.jsonObject

        val args = InstrumentationRegistry.getArguments()
        val dfineOpt = args.getString("dfine_opt") ?: "all"
        val limit = args.getString("frames")?.toInt() ?: Int.MAX_VALUE

        fun load(file: String, opt: String = "all"): Pair<OrtSession, Double> {
            val options = OrtSession.SessionOptions().apply {
                if (opt == "none") setOptimizationLevel(OrtSession.SessionOptions.OptLevel.NO_OPT)
            }
            val start = System.nanoTime()
            return env.createSession(File(dir, file).absolutePath, options) to (System.nanoTime() - start) / 1e6
        }
        val (dfineSession, dfineLoad) = load(dfine["file"]!!.jsonPrimitive.content, dfineOpt)
        val (owlSession, owlLoad) = load(owl["file"]!!.jsonPrimitive.content)
        val idsShape = shape(owl["ids_shape"]!!)
        val ids = OnnxTensor.createTensor(env, bytes(File(dir, "input_ids.i64")).asLongBuffer(), idsShape)
        val mask = OnnxTensor.createTensor(env, bytes(File(dir, "attention_mask.i64")).asLongBuffer(), idsShape)
        var peakNative = 0L

        val frames = buildJsonArray {
            for (frame in manifest["frames"]!!.jsonArray.map { it.jsonPrimitive.content }.take(limit)) {
                val d = OnnxTensor.createTensor(env, bytes(File(dir, "$frame.dfine.f32")).asFloatBuffer(), shape(dfine["shape"]!!))
                val (dLogits, dMs) = timed { logits(dfineSession, mapOf("pixel_values" to d)) }
                d.close()
                val o = OnnxTensor.createTensor(env, bytes(File(dir, "$frame.owl.f32")).asFloatBuffer(), shape(owl["shape"]!!))
                val (oLogits, oMs) = timed { logits(owlSession, mapOf("input_ids" to ids, "attention_mask" to mask, "pixel_values" to o)) }
                o.close()
                peakNative = maxOf(peakNative, Debug.getNativeHeapAllocatedSize())
                add(buildJsonObject {
                    put("frame", frame)
                    put("dfine", bestPerThing(dLogits, dfine["lists"]!!.jsonObject)); put("dfine_ms", dMs)
                    put("owl", bestPerThing(oLogits, owl["lists"]!!.jsonObject)); put("owl_ms", oMs)
                })
            }
        }
        ids.close(); mask.close(); dfineSession.close(); owlSession.close()

        val report = buildJsonObject {
            put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("android", Build.VERSION.RELEASE)
            put("runtime", "onnxruntime-android, default CPU session options; D-FINE graph optimisation: $dfineOpt")
            put("dfine_load_ms", dfineLoad); put("owl_load_ms", owlLoad)
            put("peak_native_heap_mb", peakNative / 1_000_000)
            put("things", JsonPrimitive(manifest["things"]!!.jsonArray.joinToString(",") { it.jsonPrimitive.content }))
            put("frames", frames)
        }
        File(context.getExternalFilesDir(null), "hybrid_phone_result.json").writeText(report.toString())
    }
}
