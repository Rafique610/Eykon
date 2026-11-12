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
        VectorMode.MAPPED_BLOCK -> "offheap_mapped_block" // EYKO-114 option 1
        VectorMode.MAPPED_NATIVE -> "offheap_mapped_native" // EYKO-114 option 2
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
        context.getDatabasePath(name).parentFile?.listFiles { f -> f.name.startsWith(name) && (f.name.endsWith(".vec") || f.name.endsWith(".ids")) }?.forEach { it.delete() }
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

    /**
     * EYKO-115: the vector file is written once and appended to. With MAPPED_NATIVE at `n` rows (default 100k):
     * first search (writes the file), repeat, first search after a "restart" (cache dropped, file reused), new rows
     * added straight in SQL (only they are appended), rows deleted with forget (rebuild), and a database deleted and
     * made again under the same name with different vectors (the old file must not be used). After every step the
     * scores must be bit-identical to HEAP_F32 on the same database, or the test fails.
     */
    @Test
    fun persistentFile() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val n = parseSize(InstrumentationRegistry.getArguments().getString("n") ?: "100k")
        val name = "eyko115_file_$n.db"
        val queries = TestVectors.queries("real", 512, queryCount)
        cleanUp(context, name)
        var helper = open(context, name)
        fun exact(step: String, db: SupportSQLiteDatabase) {
            VideoVectors.mode = VectorMode.MAPPED_NATIVE
            val got = queries.map { VideoVectors.scores(db, "image_vec", it).let { s -> s.ids.copyOf() to s.scores.copyOf() } }
            VideoVectors.mode = VectorMode.HEAP_F32
            VideoVectors.clearCache()
            val want = queries.map { VideoVectors.scores(db, "image_vec", it).let { s -> s.ids to s.scores } }
            val same = got.indices.count { got[it].first.contentEquals(want[it].first) && got[it].second.contentEquals(want[it].second) }
            Log.i(tag, "n=$n file step '$step': rows ${got[0].first.size}, identical to heap on $same of $queryCount queries")
            check(same == queryCount) { "$step: only $same of $queryCount identical" }
            VideoVectors.clearCache()
            VideoVectors.mode = VectorMode.MAPPED_NATIVE
        }
        fun time(step: String, db: SupportSQLiteDatabase) {
            val ms = timeMs { VideoVectors.scores(db, "image_vec", queries[0]) }
            Log.i(tag, "n=$n file step '$step': %.0f ms".format(Locale.ROOT, ms))
        }
        try {
            var db = helper.writableDatabase
            insert(db, "image_vec", "frame_id", 512, n, 31L)
            VideoVectors.mode = VectorMode.MAPPED_NATIVE
            VideoVectors.clearCache()
            time("first search, writes the file", db)
            time("repeat search", db)
            VideoVectors.clearCache()
            time("first search after restart, file reused", db)
            exact("after restart", db)
            db.beginTransaction()
            try {
                val next = TestVectors.stream("real", 512, 77L)
                db.compileStatement("INSERT INTO image_vec (frame_id, embedding) VALUES (?, ?)").use { st ->
                    for (i in 1..1000) { st.bindLong(1, (n + i).toLong()); st.bindBlob(2, TestVectors.toBlob(next())); st.executeInsert() }
                }
                db.setTransactionSuccessful()
            } finally {
                db.endTransaction()
            }
            time("1,000 new rows, appended", db)
            exact("after append", db)
            if (db.delete("image_vec", "frame_id <= 10", null) > 0) VideoVectors.forget(db, "image_vec")
            time("10 rows deleted with forget, rebuilt", db)
            exact("after delete", db)
            helper.close()
            context.deleteDatabase(name) // the vector files stay behind on purpose
            helper = open(context, name)
            db = helper.writableDatabase
            insert(db, "image_vec", "frame_id", 512, n, 99L) // same ids, different vectors
            VideoVectors.clearCache()
            time("database made again, old file present", db)
            exact("database made again", db)
        } finally {
            VideoVectors.mode = VectorMode.HEAP_F32
            VideoVectors.clearCache()
            helper.close()
            cleanUp(context, name)
        }
    }

    /**
     * EYKO-114: where does a search's time go besides scoring? Times the change check VideoVectors.scores runs on
     * every search (`SELECT COUNT(*), IFNULL(MAX(id), 0)`) and the alternatives without COUNT, at `n` rows (default 100k).
     */
    @Test
    fun changeCheckCost() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val n = parseSize(InstrumentationRegistry.getArguments().getString("n") ?: "100k")
        val name = "eyko114_check_$n.db"
        cleanUp(context, name)
        val helper = open(context, name)
        val db = helper.writableDatabase
        try {
            insert(db, "image_vec", "frame_id", 512, n, 31L)
            for (sql in listOf("SELECT COUNT(*), IFNULL(MAX(frame_id), 0) FROM image_vec", "SELECT COUNT(*) FROM image_vec",
                    "SELECT IFNULL(MAX(frame_id), 0) FROM image_vec", "SELECT MAX(rowid) FROM image_vec")) {
                db.query(sql).use { it.moveToFirst() }
                val times = List(21) { timeMs { db.query(sql).use { it.moveToFirst(); it.getLong(0) } } }.drop(1).sorted()
                Log.i(tag, "n=$n change check '$sql': median %.2f ms, worst %.2f ms".format(Locale.ROOT, times[10], times.last()))
            }
        } finally {
            helper.close()
            cleanUp(context, name)
        }
    }

    /**
     * Step 6: does Android take the memory back? Loads three tables with [mode] (argument `mode`, default
     * MAPPED_F32, `n` rows each, default 100k), logs pid, PSS and Java heap every 30 s for `seconds` (default 300)
     * while the tester opens other apps, then searches every table again and times it. A first search that is
     * much slower than a repeat means the vectors were dropped from RAM. The test runs in an instrumentation
     * process, which Android protects more than a normal app, so a kill here is strong evidence and "no kill" is weaker.
     */
    @Test
    fun holdInBackground() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val mode = VectorMode.valueOf(args.getString("mode") ?: "MAPPED_F32")
        val n = parseSize(args.getString("n") ?: "100k")
        val seconds = args.getString("seconds")?.toInt() ?: 300
        val tables = listOf(Triple("image_vec", "frame_id", 512), Triple("text_vec", "text_id", 384), Triple("audio_vec", "window_id", 512))
        val name = "eyko109_hold_$n.db"
        cleanUp(context, name)
        val helper = open(context, name)
        val db = helper.writableDatabase
        try {
            tables.forEachIndexed { i, (table, idColumn, size) -> insert(db, table, idColumn, size, n, 31L + i) }
            VideoVectors.mode = mode
            VideoVectors.clearCache()
            val queries = tables.associate { it.third to TestVectors.queries("real", it.third, 1)[0] }
            for ((table, _, size) in tables) VideoVectors.scores(db, table, queries.getValue(size))
            Log.i(tag, "hold: $mode, $n rows x 3 tables loaded, pid ${android.os.Process.myPid()}, holding $seconds s: open other apps now")
            var waited = 0
            while (waited < seconds) {
                Thread.sleep(30_000)
                waited += 30
                Log.i(tag, "hold: ${waited}s, pid ${android.os.Process.myPid()}, PSS %.0f MB, java heap %.0f MB".format(Locale.ROOT, Debug.MemoryInfo().also { Debug.getMemoryInfo(it) }.totalPss / 1024.0, javaMb()))
            }
            for ((table, _, size) in tables) {
                val first = timeMs { VideoVectors.scores(db, table, queries.getValue(size)) }
                val repeat = timeMs { VideoVectors.scores(db, table, queries.getValue(size)) }
                Log.i(tag, "hold: after $seconds s, $table search %.0f ms, repeat %.0f ms, still the same process (pid ${android.os.Process.myPid()})".format(Locale.ROOT, first, repeat))
            }
        } finally {
            VideoVectors.mode = VectorMode.HEAP_F32
            VideoVectors.clearCache()
            helper.close()
            cleanUp(context, name)
        }
    }

    private fun top(scores: FloatArray): Set<Int> = VideoVectors.rankDescending(scores).take(topK).toSet()
}
