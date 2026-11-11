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

/**
 * Card EYKO-64: what YOLOE-11S prompt-free (AGPL-3.0, academic use) costs on the Pixel, on the kept frames of the two kit
 * clips, each already letterboxed on the laptop (`src/benchmarks/yoloe_pf_phone.py inputs`). The model answers with 4,621
 * numbers for each of 8,400 boxes (about 155 MB), so the output is read in place and never copied into Java arrays.
 * Timed apart: the model run, and picking the 10 surest boxes of at least 0.10 (the best class score of every box, then the
 * top 10). Not part of the app; skipped when the files are missing.
 *
 *   adb push D:/eykon-cache/bench/detectors/yoloe_pf_phone/. /sdcard/Android/data/com.eykon.memory/files/yoloe_pf_phone/
 *   adb shell am instrument -w -e class com.eykon.memory.video.YoloePfPhoneBenchmarkTest \
 *       com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
 *   adb pull /sdcard/Android/data/com.eykon.memory/files/yoloe_pf_phone_result.json
 */
@RunWith(AndroidJUnit4::class)
class YoloePfPhoneBenchmarkTest {

    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun runYoloePfOnEveryKeptFrame() {
        val dir = File(context.getExternalFilesDir(null), "yoloe_pf_phone")
        assumeTrue("no yoloe_pf_phone files on this phone", File(dir, "manifest.json").exists())
        val manifest = Json.parseToJsonElement(File(dir, "manifest.json").readText()).jsonObject
        val wanted = manifest["boxes"]!!.jsonPrimitive.int
        val minimum = manifest["minimum"]!!.jsonPrimitive.float
        val env = OrtEnvironment.getEnvironment()
        val loadStart = System.nanoTime()
        val session = env.createSession(File(dir, manifest["file"]!!.jsonPrimitive.content).absolutePath, OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) })
        val loadMs = (System.nanoTime() - loadStart) / 1e6
        var peakNative = 0L
        var peakPss = 0

        val frames = buildJsonArray {
            for (frame in manifest["frames"]!!.jsonArray.map { it.jsonPrimitive.content }) {
                val input = ByteBuffer.wrap(File(dir, "$frame.f32").readBytes()).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
                OnnxTensor.createTensor(env, input, longArrayOf(1, 3, 640, 640)).use { image ->
                    val runStart = System.nanoTime()
                    session.run(mapOf("images" to image), setOf("output0")).use { result ->
                        val runMs = (System.nanoTime() - runStart) / 1e6
                        val output = result[0] as OnnxTensor
                        val shape = output.info.shape // 1, 4 + classes + 32, boxes
                        val boxes = shape[2].toInt()
                        val classes = shape[1].toInt() - 4 - 32
                        val values = output.floatBuffer
                        val postStart = System.nanoTime()
                        val best = FloatArray(boxes)
                        val row = FloatArray(boxes)
                        for (c in 0 until classes) {
                            values.position((4 + c) * boxes)
                            values.get(row)
                            for (b in 0 until boxes) if (row[b] > best[b]) best[b] = row[b]
                        }
                        val top = best.indices.sortedByDescending { best[it] }.take(wanted)
                        val crops = top.count { best[it] >= minimum }
                        val aboveMinimum = best.count { it >= minimum }
                        val postMs = (System.nanoTime() - postStart) / 1e6
                        peakNative = maxOf(peakNative, Debug.getNativeHeapAllocatedSize())
                        val info = Debug.MemoryInfo().also { Debug.getMemoryInfo(it) }
                        peakPss = maxOf(peakPss, info.totalPss / 1024)
                        add(buildJsonObject {
                            put("frame", frame); put("run_ms", runMs); put("post_ms", postMs)
                            put("crops", crops); put("boxes_at_least_min", aboveMinimum)
                        })
                    }
                }
            }
        }
        session.close()

        File(context.getExternalFilesDir(null), "yoloe_pf_phone_result.json").writeText(buildJsonObject {
            put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("android", Build.VERSION.RELEASE)
            put("runtime", "onnxruntime-android, default CPU session options, 4 threads")
            put("load_ms", loadMs)
            put("peak_native_heap_mb", peakNative / 1_000_000)
            put("peak_pss_mb", peakPss)
            put("frames", frames)
        }.toString())
    }
}
