package com.eykon.memory.video

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.os.Build
import android.os.Debug
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.float
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
import kotlin.math.abs
import kotlin.math.exp

/**
 * Laptop-first follow-up to docs/results/2026-10-14-detectors-open-vocabulary.md: how long the 8-bit
 * OWLv2 file takes on this phone, and whether it gives the laptop's answer. Reads what
 * `task detector-bench -- phone` wrote (model, five own frames already turned into the model's input,
 * phrase tokens, the laptop's best score per phrase). Only the model run is timed. Not part of the app.
 * Skipped when the files are not on the phone.
 *
 *   adb push D:/eykon-cache/bench/detectors/phone/. /sdcard/Android/data/com.eykon.memory/files/owl_bench/
 *   adb shell am instrument -w -e class com.eykon.memory.video.OwlPhoneBenchmarkTest \
 *       com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
 *   adb pull /sdcard/Android/data/com.eykon.memory/files/owl_bench_result.json
 */
@RunWith(AndroidJUnit4::class)
class OwlPhoneBenchmarkTest {

    private val context: Context = ApplicationProvider.getApplicationContext()

    private fun bytes(file: File): ByteBuffer = ByteBuffer.wrap(file.readBytes()).order(ByteOrder.LITTLE_ENDIAN)

    private fun shape(json: kotlinx.serialization.json.JsonElement): LongArray = json.jsonArray.map { it.jsonPrimitive.int.toLong() }.toLongArray()

    @Test
    fun timeEightBitOwlv2() {
        val dir = File(context.getExternalFilesDir(null), "owl_bench")
        assumeTrue("no owl_bench files on this phone", File(dir, "golden.json").exists())
        val golden = Json.parseToJsonElement(File(dir, "golden.json").readText()).jsonObject
        val idsShape = shape(golden["ids_shape"]!!)
        val pixelsShape = shape(golden["pixels_shape"]!!)
        val env = OrtEnvironment.getEnvironment()

        val loadStart = System.nanoTime()
        val session = env.createSession(File(dir, "owlv2_q8.onnx").absolutePath, OrtSession.SessionOptions())
        val loadMs = (System.nanoTime() - loadStart) / 1e6
        val ids = OnnxTensor.createTensor(env, bytes(File(dir, "input_ids.i64")).asLongBuffer(), idsShape)
        val mask = OnnxTensor.createTensor(env, bytes(File(dir, "attention_mask.i64")).asLongBuffer(), idsShape)
        var peakNative = 0L

        val frames = buildJsonArray {
            for ((frame, laptop) in golden["frames"]!!.jsonObject) {
                val pixels = OnnxTensor.createTensor(env, bytes(File(dir, "$frame.f32")).asFloatBuffer(), pixelsShape)
                val start = System.nanoTime()
                val best = session.run(mapOf("input_ids" to ids, "attention_mask" to mask, "pixel_values" to pixels), setOf("logits")).use { out ->
                    @Suppress("UNCHECKED_CAST")
                    val logits = (out[0].value as Array<Array<FloatArray>>)[0] // boxes x phrases
                    FloatArray(logits[0].size) { q -> 1 / (1 + exp(-logits.maxOf { it[q] })) }
                }
                val runMs = (System.nanoTime() - start) / 1e6
                pixels.close()
                peakNative = maxOf(peakNative, Debug.getNativeHeapAllocatedSize())
                val diff = best.indices.maxOf { abs(best[it] - laptop.jsonArray[it].jsonPrimitive.float) }
                add(buildJsonObject {
                    put("frame", frame); put("ms", runMs); put("max_diff_from_laptop", diff)
                    put("best", buildJsonArray { best.forEach { add(kotlinx.serialization.json.JsonPrimitive(it)) } })
                })
            }
        }
        ids.close(); mask.close(); session.close()

        val report = buildJsonObject {
            put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("android", Build.VERSION.RELEASE)
            put("model", "Xenova/owlv2-base-patch16-ensemble onnx/model_quantized.onnx")
            put("runtime", "onnxruntime-android, default CPU session options")
            put("load_ms", loadMs)
            put("peak_native_heap_mb", peakNative / 1_000_000)
            put("phrases", golden["phrases"]!!)
            put("frames", frames)
        }
        File(context.getExternalFilesDir(null), "owl_bench_result.json").writeText(report.toString())
    }
}
