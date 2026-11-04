package com.eykon.memory.video

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Bitmap
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMetadataRetriever
import android.os.BatteryManager
import android.os.Build
import android.os.Debug
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.eykon.memory.ml.vision.ImageEmbedder
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Card EYKO-45, the phone half: for every clip in the app's files/eval_clips folder, run
 *   ours     the app's own three stages (pull frames, cheap filters, drop repeats),
 *   uniform  the same number of frames, evenly spaced,
 *   iframes  the frames the video file already stores in full,
 * three times each, and write what each kept and how long it took to files/keyframe_bench.json.
 * Not a pass/fail test: it is skipped when the clips or the model are not on the phone.
 *
 *   adb push <clips> /sdcard/Android/data/com.eykon.memory/files/eval_clips/
 *   adb shell am instrument -w -e class com.eykon.memory.video.KeyframeBenchmarkTest \
 *       com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
 *   adb pull /sdcard/Android/data/com.eykon.memory/files/keyframe_bench.json
 */
@RunWith(AndroidJUnit4::class)
class KeyframeBenchmarkTest {

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val runs = 3

    private fun batteryTemperature(): Double =
        (context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0) ?: 0) / 10.0

    private fun batteryLevel(): Int =
        context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1

    private fun ms(block: () -> Unit): Long = System.nanoTime().let { start -> block(); (System.nanoTime() - start) / 1_000_000 }

    private fun times(values: List<Double>): JsonArray = buildJsonArray { values.forEach { add(JsonPrimitive(Math.round(it * 1000) / 1000.0)) } }

    private fun durationS(file: File): Double {
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(file.absolutePath)
            return (retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: 0L) / 1000.0
        } finally {
            retriever.release()
        }
    }

    /** Times of the frames the file stores in full (sync samples). Reads the file's index only: nothing is decoded. */
    private fun syncTimes(file: File): List<Double> {
        val extractor = MediaExtractor()
        try {
            extractor.setDataSource(file.absolutePath)
            val track = (0 until extractor.trackCount).first { extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)!!.startsWith("video/") }
            extractor.selectTrack(track)
            val out = ArrayList<Double>()
            while (extractor.sampleTime >= 0) {
                if (extractor.sampleFlags and MediaExtractor.SAMPLE_FLAG_SYNC != 0) out.add(extractor.sampleTime / 1e6)
                extractor.advance()
            }
            return out
        } finally {
            extractor.release()
        }
    }

    private fun saveSyncFrames(file: File, dir: File, at: List<Double>) {
        dir.deleteRecursively(); dir.mkdirs()
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(file.absolutePath)
            at.forEachIndexed { i, t ->
                val bitmap = retriever.getScaledFrameAtTime((t * 1e6).toLong(), MediaMetadataRetriever.OPTION_CLOSEST_SYNC, VideoSplit.FRAME_MAX_SIDE, VideoSplit.FRAME_MAX_SIDE) ?: return@forEachIndexed
                File(dir, "%06d.jpg".format(i + 1)).outputStream().use { bitmap.compress(Bitmap.CompressFormat.JPEG, VideoSplit.JPEG_QUALITY, it) }
                bitmap.recycle()
            }
        } finally {
            retriever.release()
        }
    }

    private fun openDb(): Pair<SupportSQLiteOpenHelper, SupportSQLiteDatabase> {
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        val helper = FrameworkSQLiteOpenHelperFactory().create(
            SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build(),
        )
        return helper to helper.writableDatabase
    }

    @Test
    fun measureEveryClip() {
        val clipsDir = File(context.getExternalFilesDir(null), "eval_clips")
        val clips = clipsDir.listFiles { f -> f.extension.lowercase() == "mp4" }?.sortedBy { it.name }.orEmpty()
        assumeTrue("no clips in ${clipsDir.path}", clips.isNotEmpty())
        assumeTrue("image model not on this phone", ImageEmbedder.modelFile(context).exists())

        val work = File(context.cacheDir, "keyframe_bench").apply { deleteRecursively(); mkdirs() }
        val startTemperature = batteryTemperature()
        val startLevel = batteryLevel()
        val startedAt = System.currentTimeMillis()
        ImageEmbedder.embed(context, Bitmap.createBitmap(256, 256, Bitmap.Config.ARGB_8888)) // load the model before timing anything

        val results = buildJsonArray {
            for (clip in clips) {
                val duration = durationS(clip)
                add(buildJsonObject {
                    put("clip", clip.name)
                    put("duration_s", duration)

                    // ── ours ────────────────────────────────────────────────────────
                    var keptTimes = emptyList<Double>()
                    put("ours", buildJsonArray {
                        repeat(runs) { run ->
                            val (helper, db) = openDb()
                            try {
                                val id = "c${clips.indexOf(clip)}r$run"
                                val folder = File(work, id).apply { mkdirs() }
                                val copy = File(folder, "$id.mp4").also { clip.copyTo(it, overwrite = true) }
                                VideoRepository { db }.insert(
                                    Video(videoId = id, filePath = copy.absolutePath, recordedAt = "2026-10-12T00:00:00Z", createdAt = "2026-10-12T00:00:00Z", durationS = duration),
                                )
                                val split = ms { VideoSplit.run(db, id) }
                                val filter = ms { VideoFilter.run(db, id) }
                                val dedup = ms { VideoDedup.run(db, id) }
                                val frames = db.query("SELECT t_s, kept, drop_reason FROM frames WHERE video_id = ? ORDER BY frame_no", arrayOf(id)).use { c ->
                                    buildList { while (c.moveToNext()) add(Triple(c.getDouble(0), c.getInt(1), if (c.isNull(2)) null else c.getString(2))) }
                                }
                                keptTimes = frames.filter { it.second == 1 }.map { it.first }
                                val reasons = HashMap<String, Int>()
                                frames.mapNotNull { it.third }.forEach { reason ->
                                    val key = if (reason.startsWith("duplicate")) "duplicate" else reason
                                    reasons[key] = (reasons[key] ?: 0) + 1
                                }
                                val embedded = VideoDedup.readVectors(File(folder, VideoDedup.VECTORS_FILE)).size
                                add(buildJsonObject {
                                    put("split_ms", split); put("filter_ms", filter); put("dedup_ms", dedup)
                                    put("frames_pulled", frames.size); put("kept", keptTimes.size)
                                    put("dropped", buildJsonObject { reasons.forEach { (k, v) -> put(k, v) } })
                                    put("unique_vectors", embedded)
                                    put("native_heap_mb", Debug.getNativeHeapAllocatedSize() / 1_000_000)
                                    put("kept_times", times(keptTimes))
                                })
                                folder.deleteRecursively()
                            } finally {
                                helper.close()
                            }
                        }
                    })

                    // ── uniform: the same number of frames, evenly spaced ───────────
                    val n = keptTimes.size.coerceAtLeast(1)
                    val uniform = List(n) { (it + 0.5) * duration / n }
                    put("uniform", buildJsonObject {
                        put("kept_times", times(uniform))
                        put("ms", buildJsonArray {
                            repeat(runs) {
                                val dir = File(work, "uniform").apply { deleteRecursively(); mkdirs() }
                                add(JsonPrimitive(ms { FrameExtractor.decodeInOnePass(clip.absolutePath, dir, uniform, VideoSplit.FRAME_MAX_SIDE, VideoSplit.JPEG_QUALITY) }))
                            }
                        })
                    })

                    // ── iframes: what the file already stores in full ───────────────
                    val sync = syncTimes(clip)
                    put("iframes", buildJsonObject {
                        put("kept_times", times(sync))
                        put("list_ms", buildJsonArray { repeat(runs) { add(JsonPrimitive(ms { syncTimes(clip) })) } })
                        put("save_ms", buildJsonArray { repeat(runs) { add(JsonPrimitive(ms { saveSyncFrames(clip, File(work, "iframes"), sync) })) } })
                    })
                })
            }
        }

        val report = buildJsonObject {
            put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("android", Build.VERSION.RELEASE)
            put("build", "debug")
            put("runs_per_method", runs)
            put("battery_level_start", startLevel); put("battery_level_end", batteryLevel())
            put("battery_temp_start_c", startTemperature); put("battery_temp_end_c", batteryTemperature())
            put("wall_seconds", (System.currentTimeMillis() - startedAt) / 1000)
            put("clips", results)
        }
        File(context.getExternalFilesDir(null), "keyframe_bench.json").writeText(report.toString())
        work.deleteRecursively()
    }
}
