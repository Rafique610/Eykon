package com.eykon.memory.video

import android.content.Context
import android.os.Build
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.spike.BenchSheet
import com.eykon.memory.spike.TestVectors
import com.eykon.memory.spike.battery
import com.eykon.memory.spike.parseSize
import com.eykon.memory.spike.timeMs
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.Locale

/**
 * EYKO-102: how long the app's own search (VideoSearch.frames) takes on this phone, end to end,
 * and how much of that is VideoVectors.knn.
 *
 * It builds a memory with the app's schema in the proportions we measured: ready videos of 600
 * kept frames each (about 45 min at 13.4 kept frames a minute), [dropped] dropped frames per kept
 * one (the Ego4D phone memory of 20 Oct had 5,939 frames for 460 kept: about 12), and for every
 * kept frame a caption and a real vector (EYKO-100 assets). 1 warm-up search + 20 queries x runs.
 * Every hit of every query (frame, window, score) is written to a text file, so the results before
 * and after a change can be compared.
 *
 * Arguments: sizes (kept frames, default 5k,20k,50k,100k), runs (default 5), dropped (default 12),
 * label (goes into the file names, e.g. before / after), commit.
 */
@RunWith(AndroidJUnit4::class)
class VideoSearchSpeedTest {

    private val tag = "EYKO102"
    private val perVideo = 600

    @Test
    fun searchEndToEnd() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "5k,20k,50k,100k").split(",").map { parseSize(it) }
        val runs = args.getString("runs")?.toInt() ?: 5
        val dropped = args.getString("dropped")?.toInt() ?: 12
        val label = args.getString("label") ?: "current"
        val sheet = BenchSheet(context, tag, "eyko102-search-$label", args.getString("commit") ?: "unknown", TestVectors.label("real"))
        Log.i(tag, "search: sizes $sizes, runs $runs, dropped per kept $dropped, label $label")
        val queries = TestVectors.queries("real", 512, 21) // the first one is the warm-up
        val model = Build.MODEL.replace(Regex("[^A-Za-z0-9]+"), "_")

        for (n in sizes) {
            val name = "eyko102_search_$n.db"
            context.deleteDatabase(name)
            val helper = open(context, name)
            val db = helper.writableDatabase
            try {
                VideoVectors.clearCache()
                val buildMs = timeMs { fill(db, n, dropped) }
                val fileMb = context.getDatabasePath(name).length() / 1e6
                Log.i(tag, "n=$n built: %.0f ms, file %.1f MB, %d frame rows".format(Locale.ROOT, buildMs, fileMb, n * (dropped + 1)))
                val note = "kept=$n; dropped_per_kept=$dropped; frames_per_video=$perVideo"
                try {
                    // The first search after opening the app also loads the vectors into memory.
                    val first = timeMs { VideoSearch.frames(db, "query", VideoSearch.POOL) { queries[0] } }
                    sheet.row("app_search_first", 512, n, "", listOf(first), fileMb, null, "$note; first search loads the vectors")
                    for (run in 1..runs) {
                        val tempStart = battery(context).first
                        sheet.row("app_search_frames", 512, n, "$run", queries.drop(1).map { q -> timeMs { VideoSearch.frames(db, "query", VideoSearch.POOL) { q } } }, fileMb, tempStart, note)
                    }
                    for (run in 1..runs) {
                        val tempStart = battery(context).first
                        sheet.row("app_knn_all", 512, n, "$run", queries.drop(1).map { q -> timeMs { VideoVectors.knn(db, "image_vec", q, Int.MAX_VALUE) } }, fileMb, tempStart, note)
                    }
                    File(sheet.outDir, "eyko102-hits-$label-$model-$n.txt").printWriter().use { out ->
                        queries.drop(1).forEachIndexed { qi, q ->
                            VideoSearch.frames(db, "query", VideoSearch.POOL) { q }.forEach { h ->
                                out.println("%d %d %.3f %.3f %.6f".format(Locale.ROOT, qi, h.frameId, h.startS, h.endS, h.score))
                            }
                        }
                    }
                } catch (e: OutOfMemoryError) {
                    sheet.row("app_search_frames", 512, n, "", null, fileMb, null, "$note; OutOfMemoryError: ${e.message}")
                }
            } finally {
                helper.close()
                VideoVectors.clearCache()
                context.deleteDatabase(name)
            }
        }
        sheet.done()
        Log.i(tag, "hits files: adb pull ${sheet.outDir.absolutePath}/ (eyko102-hits-$label-*.txt)")
    }

    private fun open(context: Context, name: String): SupportSQLiteOpenHelper {
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        return FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(name).callback(callback).build())
    }

    /** [kept] kept frames (caption + real vector each) with [dropped] dropped frames after each, in ready videos. */
    private fun fill(db: SupportSQLiteDatabase, kept: Int, dropped: Int) {
        val nextVector = TestVectors.stream("real", 512, 31)
        val step = 4.5 / (dropped + 1) // a kept frame every 4.5 s (13.4 a minute)
        db.beginTransaction()
        try {
            val video = db.compileStatement("INSERT INTO videos (video_id, file_path, recorded_at, duration_s, status, created_at) VALUES (?, ?, ?, ?, 'ready', ?)")
            val frame = db.compileStatement("INSERT INTO frames (id, video_id, frame_no, t_s, path, kept) VALUES (?, ?, ?, ?, ?, ?)")
            val scene = db.compileStatement("INSERT INTO scene_records (frame_id, objects, caption, source) VALUES (?, '[]', ?, 'A')")
            val vector = db.compileStatement("INSERT INTO image_vec (frame_id, embedding) VALUES (?, ?)")
            var id = 0L
            for (k in 0 until kept) {
                val v = k / perVideo
                val videoId = "v$v"
                val frameNo = (k % perVideo) * (dropped + 1)
                if (k % perVideo == 0) {
                    video.bindString(1, videoId)
                    video.bindString(2, "/bench/videos/$videoId/$videoId.mp4")
                    video.bindString(3, "2026-10-%02dT10:00:00Z".format(Locale.ROOT, 1 + v % 28))
                    video.bindDouble(4, perVideo * 4.5)
                    video.bindString(5, "2026-11-04T10:00:00Z")
                    video.executeInsert()
                }
                for (d in 0..dropped) {
                    id++
                    frame.bindLong(1, id)
                    frame.bindString(2, videoId)
                    frame.bindLong(3, (frameNo + d).toLong())
                    frame.bindDouble(4, (frameNo + d) * step)
                    frame.bindString(5, "$videoId/frames/%06d.jpg".format(Locale.ROOT, frameNo + d))
                    frame.bindLong(6, if (d == 0) 1 else 0)
                    frame.executeInsert()
                    if (d == 0) {
                        scene.bindLong(1, id)
                        scene.bindString(2, "caption of frame $id")
                        scene.executeInsert()
                        vector.bindLong(1, id)
                        vector.bindBlob(2, TestVectors.toBlob(nextVector()))
                        vector.executeInsert()
                    }
                }
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }
}
