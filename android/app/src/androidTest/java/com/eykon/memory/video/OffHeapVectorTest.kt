package com.eykon.memory.video

import android.content.Context
import android.os.Debug
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
import java.util.Locale

/**
 * EYKO-109 (O1): keep the vectors outside the Java heap and/or smaller. Runs the app's own
 * VideoVectors with each [VectorMode] on the phone. Results go to logcat (tag EYKO109) and a CSV in
 * files/results (shared format). Arguments (`-e name value`): sizes (default 5k,20k,50k,100k),
 * modes (comma list of VectorMode names, default all), runs (default 5), commit.
 */
@RunWith(AndroidJUnit4::class)
class OffHeapVectorTest {

    private val tag = "EYKO109"
    private val queryCount = 20
    private val topK = 20

    private fun method(mode: VectorMode) = when (mode) {
        VectorMode.HEAP_F32 -> "heap_f32"
        VectorMode.DIRECT_F32 -> "offheap_f32"
        VectorMode.DIRECT_F16 -> "offheap_f16"
        VectorMode.DIRECT_I8 -> "offheap_i8_rescore"
        VectorMode.MAPPED_F32 -> "offheap_mapped_f32"
    }

    private fun modes() = (InstrumentationRegistry.getArguments().getString("modes") ?: VectorMode.entries.joinToString(","))
        .split(",").map { VectorMode.valueOf(it.trim()) }

    private fun open(context: Context, name: String): SupportSQLiteOpenHelper {
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        return FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(name).callback(callback).build())
    }

    /** [n] vectors into [table], ids 1..n. Foreign keys are off (the helper does not switch them on). */
    private fun insert(db: SupportSQLiteDatabase, table: String, idColumn: String, size: Int, n: Int, seed: Long) {
        val next = TestVectors.stream("real", size, seed)
        db.beginTransaction()
        try {
            val statement = db.compileStatement("INSERT INTO $table ($idColumn, embedding) VALUES (?, ?)")
            for (i in 1..n) {
                statement.bindLong(1, i.toLong())
                statement.bindBlob(2, TestVectors.toBlob(next()))
                statement.executeInsert()
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    private fun settle(): Double {
        repeat(2) { Runtime.getRuntime().gc(); System.runFinalization() }
        Thread.sleep(300)
        return Debug.MemoryInfo().also { Debug.getMemoryInfo(it) }.totalPss / 1024.0
    }

    private fun javaMb() = (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1e6
    private fun nativeMb() = Debug.getNativeHeapAllocatedSize() / 1e6

    /** Remove the mapped-vector files MAPPED_F32 leaves next to the database. */
    private fun deleteVec(context: Context, name: String) {
        context.getDatabasePath(name).parentFile?.listFiles { f -> f.name.startsWith(name) && f.name.endsWith(".vec") }?.forEach { it.delete() }
    }

    private fun cleanUp(context: Context, name: String) {
        deleteVec(context, name)
        context.deleteDatabase(name)
    }

    /**
     * B4: all three tables (image 512, text 384, audio-sized 512, n rows each: the worst case) loaded
     * through VideoVectors.scores with each mode. PSS, Java heap and native heap before and after,
     * how many tables loaded, and any OutOfMemoryError.
     */
    @Test
    fun memoryAllTables() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "5k,20k,50k,100k").split(",").map { parseSize(it) }
        val sheet = BenchSheet(context, tag, "eyko109-memory", args.getString("commit") ?: "unknown", TestVectors.label("real"))
        val tables = listOf(Triple("image_vec", "frame_id", 512), Triple("text_vec", "text_id", 384), Triple("audio_vec", "window_id", 512))
        val queries = tables.associate { it.third to TestVectors.queries("real", it.third, 1)[0] }
        for (n in sizes) {
            val name = "eyko109_memory_$n.db"
            cleanUp(context, name)
            val helper = open(context, name)
            val db = helper.writableDatabase
            try {
                tables.forEachIndexed { i, (table, idColumn, size) -> insert(db, table, idColumn, size, n, 31L + i) }
                val fileMb = context.getDatabasePath(name).length() / 1e6
                for (mode in modes()) {
                    VideoVectors.mode = mode
                    VideoVectors.clearCache()
                    val before = Triple(settle(), javaMb(), nativeMb())
                    var loaded = 0
                    var failed = ""
                    for ((table, _, size) in tables) {
                        try {
                            VideoVectors.scores(db, table, queries.getValue(size))
                            loaded++
                        } catch (e: OutOfMemoryError) {
                            failed = "OutOfMemoryError while loading $table: ${e.message}"
                            break
                        }
                    }
                    val after = Triple(settle(), javaMb(), nativeMb())
                    val note = "pss_before_mb=%.0f; pss_after_mb=%.0f; java_before_mb=%.0f; java_after_mb=%.0f; native_before_mb=%.0f; native_after_mb=%.0f; tables_loaded=%d of 3%s".format(
                        Locale.ROOT, before.first, after.first, before.second, after.second, before.third, after.third, loaded, if (failed.isEmpty()) "" else "; $failed",
                    )
                    Log.i(tag, "n=$n ${method(mode)}: $note")
                    sheet.row("memory_${method(mode)}", tables.sumOf { it.third }, n, "", null, fileMb, null, note)
                    VideoVectors.clearCache()
                    deleteVec(context, name)
                }
            } finally {
                VideoVectors.mode = VectorMode.HEAP_F32
                VideoVectors.clearCache()
                helper.close()
                cleanUp(context, name)
            }
        }
        sheet.done()
    }

    /**
     * Speed and answers, image table only (512, real vectors): 1 warm-up + [queryCount] queries x runs
     * per mode, and against the heap mode: how many queries give bit-identical scores, recall@20.
     */
    @Test
    fun speedAndAnswers() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "5k,20k,50k,100k").split(",").map { parseSize(it) }
        val runs = args.getString("runs")?.toInt() ?: 5
        val sheet = BenchSheet(context, tag, "eyko109-speed", args.getString("commit") ?: "unknown", TestVectors.label("real"))
        val queries = TestVectors.queries("real", 512, queryCount + 1)
        for (n in sizes) {
            val name = "eyko109_speed_$n.db"
            cleanUp(context, name)
            val helper = open(context, name)
            val db = helper.writableDatabase
            try {
                insert(db, "image_vec", "frame_id", 512, n, 31L)
                val fileMb = context.getDatabasePath(name).length() / 1e6
                VideoVectors.mode = VectorMode.HEAP_F32
                VideoVectors.clearCache()
                val reference = try {
                    queries.drop(1).map { VideoVectors.scores(db, "image_vec", it).scores.copyOf() }
                } catch (e: OutOfMemoryError) {
                    null
                }
                for (mode in modes()) {
                    VideoVectors.mode = mode
                    VideoVectors.clearCache()
                    try {
                        val first = timeMs { VideoVectors.scores(db, "image_vec", queries[0]) } // loads the table
                        var note = "first search (loads the table) %.0f ms".format(Locale.ROOT, first)
                        if (reference != null) {
                            val got = queries.drop(1).map { VideoVectors.scores(db, "image_vec", it).scores }
                            val identical = got.indices.count { java.util.Arrays.equals(got[it], reference[it]) }
                            val overlap = got.indices.sumOf { top(got[it]).intersect(top(reference[it])).size }
                            note += "; identical scores on $identical of $queryCount queries; recall@$topK %.4f (%d of %d)".format(
                                Locale.ROOT, overlap.toDouble() / (queryCount * topK), overlap, queryCount * topK,
                            )
                        }
                        Log.i(tag, "n=$n ${method(mode)}: $note")
                        for (run in 1..runs) {
                            val tempStart = battery(context).first
                            sheet.row(method(mode), 512, n, "$run", queries.drop(1).map { q -> timeMs { VideoVectors.scores(db, "image_vec", q) } }, fileMb, tempStart, note)
                        }
                    } catch (e: OutOfMemoryError) {
                        sheet.row(method(mode), 512, n, "", null, fileMb, null, "OutOfMemoryError: ${e.message}")
                    }
                }
            } finally {
                VideoVectors.mode = VectorMode.HEAP_F32
                VideoVectors.clearCache()
                helper.close()
                cleanUp(context, name)
            }
        }
        sheet.done()
    }

    private fun top(scores: FloatArray): Set<Int> = VideoVectors.rankDescending(scores).take(topK).toSet()
}
