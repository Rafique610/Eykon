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
 * Card EYKO-32: YOLOE-11L (AGPL-3.0, academic use) with its word list fixed to six own phrases, on all
 * 50 own frames, each already letterboxed on the laptop. Writes each phrase's best score and the time
 * per frame; `task yoloe-phone -- score` scores them. Only the model run is timed. Not part of the app;
 * skipped when the files are missing.
 *
 *   adb push D:/eykon-cache/bench/detectors/yoloe_phone/. /sdcard/Android/data/com.eykon.memory/files/yoloe_phone/
 *   adb shell am instrument -w -e class com.eykon.memory.video.YoloePhoneBenchmarkTest \
 *       com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
 *   adb pull /sdcard/Android/data/com.eykon.memory/files/yoloe_phone_result.json
 */
@RunWith(AndroidJUnit4::class)
class YoloePhoneBenchmarkTest {

    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun runYoloeOnEveryFrame() {
        val dir = File(context.getExternalFilesDir(null), "yoloe_phone")
        assumeTrue("no yoloe_phone files on this phone", File(dir, "manifest.json").exists())
        val manifest = Json.parseToJsonElement(File(dir, "manifest.json").readText()).jsonObject
        val env = OrtEnvironment.getEnvironment()
        val loadStart = System.nanoTime()
        val session = env.createSession(File(dir, manifest["file"]!!.jsonPrimitive.content).absolutePath, OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) })
        val loadMs = (System.nanoTime() - loadStart) / 1e6
        val lists = manifest["lists"]!!.jsonObject.mapValues { (_, v) -> v.jsonArray.single().jsonPrimitive.int }
        var peakNative = 0L

        val frames = buildJsonArray {
            for (frame in manifest["frames"]!!.jsonArray.map { it.jsonPrimitive.content }) {
                val buffer = ByteBuffer.wrap(File(dir, "$frame.f32").readBytes()).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
                OnnxTensor.createTensor(env, buffer, longArrayOf(1, 3, 640, 640)).use { input ->
                    val start = System.nanoTime()
                    @Suppress("UNCHECKED_CAST")
                    val rows = session.run(mapOf("images" to input), setOf("output0")).use { (it[0].value as Array<Array<FloatArray>>)[0] }
                    val ms = (System.nanoTime() - start) / 1e6
                    peakNative = maxOf(peakNative, Debug.getNativeHeapAllocatedSize())
                    add(buildJsonObject {
                        put("frame", frame); put("ms", ms)
                        put("best", buildJsonObject { lists.forEach { (thing, c) -> put(thing, Math.round(rows[4 + c].max() * 1000.0) / 1000.0) } })
                    })
                }
            }
        }
        session.close()

        File(context.getExternalFilesDir(null), "yoloe_phone_result.json").writeText(buildJsonObject {
            put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("android", Build.VERSION.RELEASE)
            put("runtime", "onnxruntime-android, default CPU session options, 4 threads")
            put("load_ms", loadMs)
            put("peak_native_heap_mb", peakNative / 1_000_000)
            put("frames", frames)
        }.toString())
    }
}
