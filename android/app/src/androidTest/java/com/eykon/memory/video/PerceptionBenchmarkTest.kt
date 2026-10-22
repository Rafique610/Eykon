package com.eykon.memory.video

import android.content.Context
import android.media.MediaMetadataRetriever
import android.os.Build
import android.os.Debug
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.vision.ImageEmbedder
import com.eykon.memory.ml.vision.ObjectDetector
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Card EYKO-9, the measurement: every clip in files/eval_clips goes through the app's own stages
 * (pull frames, cheap filters, drop repeats), then every frame that was kept is described by
 * Option A. Writes what was found and how long it took to files/perception_bench.json and copies
 * the frames to files/perception_frames so they can be labelled by hand.
 * Not a pass/fail test: it is skipped when the clips or a model are not on the phone.
 *
 *   adb shell am instrument -w -e class com.eykon.memory.video.PerceptionBenchmarkTest \
 *       com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
 *   adb pull /sdcard/Android/data/com.eykon.memory/files/perception_frames
 *   adb pull /sdcard/Android/data/com.eykon.memory/files/perception_bench_yolox_tiny.json
 * Add `-e detector yolox_nano.onnx` to measure another YOLOX file pushed to the models folder.
 */
@RunWith(AndroidJUnit4::class)
class PerceptionBenchmarkTest {

    private val context: Context = ApplicationProvider.getApplicationContext()

    private class Kept(val id: Long, val frameNo: Int, val tS: Double, val path: String)

    private fun ms(block: () -> Unit): Double = System.nanoTime().let { start -> block(); (System.nanoTime() - start) / 1e6 }

    private fun durationS(file: File): Double {
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(file.absolutePath)
            return (retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: 0L) / 1000.0
        } finally {
            retriever.release()
        }
    }

    @Test
    fun describeEveryKeptFrame() {
        val clips = File(context.getExternalFilesDir(null), "eval_clips").listFiles { f -> f.extension.lowercase() == "mp4" }?.sortedBy { it.name }.orEmpty()
        assumeTrue("no clips in files/eval_clips", clips.isNotEmpty())
        // -e detector yolox_nano.onnx measures another YOLOX file; the result file carries its name
        val detector = InstrumentationRegistry.getArguments().getString("detector") ?: ObjectDetector.MODEL_FILE
        ObjectDetector.useModel(detector)
        assumeTrue("a model is not on this phone", ObjectDetector.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists())

        val work = File(context.cacheDir, "perception_bench").apply { deleteRecursively(); mkdirs() }
        val framesOut = File(context.getExternalFilesDir(null), "perception_frames").apply { deleteRecursively(); mkdirs() }
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        val helper = FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build())
        val db = helper.writableDatabase
        var peakNative = 0L
        var peakJava = 0L
        val runtime = Runtime.getRuntime()

        val frames = buildJsonArray {
            for (clip in clips) {
                val id = clip.nameWithoutExtension
                val folder = File(work, id).apply { mkdirs() }
                val copy = File(folder, "$id.mp4").also { clip.copyTo(it, overwrite = true) }
                VideoRepository { db }.insert(
                    Video(videoId = id, filePath = copy.absolutePath, recordedAt = "2026-10-13T00:00:00Z", createdAt = "2026-10-13T00:00:00Z", durationS = durationS(copy)),
                )
                VideoSplit.run(db, id)
                VideoFilter.run(db, id)
                VideoDedup.run(db, id)
                val saved = VideoDedup.readVectors(File(folder, VideoDedup.VECTORS_FILE))
                val kept = db.query("SELECT id, frame_no, t_s, path FROM frames WHERE video_id = ? AND kept = 1 ORDER BY frame_no", arrayOf(id)).use { c ->
                    buildList { while (c.moveToNext()) add(Kept(c.getLong(0), c.getInt(1), c.getDouble(2), c.getString(3))) }
                }
                for (frame in kept) {
                    val file = File(work, frame.path)
                    val name = "${id}_%06d.jpg".format(frame.frameNo)
                    file.copyTo(File(framesOut, name), overwrite = true)

                    lateinit var seen: Perception
                    val fullMs = ms { seen = OptionA.describe(context, file) } // detector + image model + phrases
                    val reuseMs = ms { OptionA.describe(context, file, saved[frame.id]) } // the vector the dedup stage saved
                    peakNative = maxOf(peakNative, Debug.getNativeHeapAllocatedSize())
                    peakJava = maxOf(peakJava, runtime.totalMemory() - runtime.freeMemory())
                    add(buildJsonObject {
                        put("frame", name); put("clip", id); put("t_s", frame.tS)
                        put("objects", buildJsonArray { seen.objects.forEach { add(buildJsonObject { put("label", it.label); put("conf", it.conf) }) } })
                        put("people", seen.people)
                        put("place", seen.place); put("action", seen.action)
                        put("full_ms", fullMs); put("with_saved_vector_ms", reuseMs)
                    })
                }
            }
        }
        helper.close()
        work.deleteRecursively()

        val report = buildJsonObject {
            put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("android", Build.VERSION.RELEASE)
            put("build", "debug")
            put("detector", detector)
            put("detector_conf", OptionA.DETECTOR_CONF)
            put("prompt_min", OptionA.PROMPT_MIN)
            put("peak_native_heap_mb", peakNative / 1_000_000)
            put("peak_java_heap_mb", peakJava / 1_000_000)
            put("frames", frames)
        }
        ObjectDetector.useModel(ObjectDetector.MODEL_FILE)
        File(context.getExternalFilesDir(null), "perception_bench_${detector.removeSuffix(".onnx")}.json").writeText(report.toString())
    }
}
