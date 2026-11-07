package com.eykon.memory.spike

import android.content.Context
import android.os.Debug
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.Locale

/**
 * EYKO-108 (route R4, throwaway): our own NDK build of SQLite with sqlite-vec compiled in, opened
 * through a small JNI layer. Logcat tag EYKO31 (versions) and EYKO108; CSV in files/results.
 * Arguments (`-e name value`): neon (true default, false = the no-NEON build), sizes (default
 * 1k,5k,20k,50k,100k), runs (default 5), commit. Methods: sqlite_vec_static, sqlite_vec_static_noneon.
 * Run one test per process (`am instrument -e class ...#name`): the library loads once.
 */
@RunWith(AndroidJUnit4::class)
class RouteR4StaticTest {

    private val tag = "EYKO108"
    private val topK = 20
    private val queryCount = 20

    private val neon get() = InstrumentationRegistry.getArguments().getString("neon") != "false"
    private val method get() = if (neon) "sqlite_vec_static" else "sqlite_vec_static_noneon"

    private fun open(context: Context, name: String): Pair<Long, Double> {
        val file = context.getDatabasePath(name)
        file.parentFile?.mkdirs()
        file.delete()
        var db = 0L
        val ms = timeMs { db = NativeSqlite.nativeOpen(file.absolutePath) }
        check(db != 0L) { "open failed" }
        return db to ms
    }

    private fun exec(db: Long, sql: String) {
        NativeSqlite.nativeExec(db, sql)?.let { error("$sql -> $it") }
    }

    /** C1 and step 5: versions, vec_version(), an fts5 table; says plainly what failed. */
    @Test
    fun versionsAndFts() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        NativeSqlite.load(neon)
        val (db, openMs) = open(context, "eyko108_versions.db")
        try {
            Log.i("EYKO31", "route R4 ($method): sqlite_version() = ${NativeSqlite.scalar(db, "SELECT sqlite_version()")}, open %.1f ms".format(Locale.ROOT, openMs))
            try {
                Log.i("EYKO31", "route R4 ($method): vec_version() = ${NativeSqlite.scalar(db, "SELECT vec_version()")}")
            } catch (e: Exception) {
                Log.i("EYKO31", "route R4 ($method): vec_version() failed: ${e.message}")
            }
            for (sql in listOf("CREATE VIRTUAL TABLE t_fts5 USING fts5(x)", "CREATE VIRTUAL TABLE t_vec USING vec0(embedding float[4])")) {
                val error = NativeSqlite.nativeExec(db, sql)
                Log.i("EYKO31", "route R4 ($method): $sql -> ${error ?: "ok"}")
            }
            exec(db, "INSERT INTO t_vec(rowid, embedding) VALUES (1, X'0000803F000000000000000000000000')")
            Log.i("EYKO31", "route R4 ($method): vec0 insert and select -> ${NativeSqlite.scalar(db, "SELECT rowid FROM t_vec WHERE embedding MATCH X'0000803F000000000000000000000000' ORDER BY distance LIMIT 1")}")
        } finally {
            NativeSqlite.nativeClose(db)
        }
    }

    /**
     * The shared protocol on one table (image, 512, real vectors): insert n rows into a vec0 table,
     * 1 warm-up + [queryCount] queries x runs, top 20; recall@20 against exact search computed in
     * the same pass over the vector stream (no copy of the vectors is kept).
     */
    @Test
    fun sweep() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "1k,5k,20k,50k,100k").split(",").map { parseSize(it) }
        val runs = args.getString("runs")?.toInt() ?: 5
        NativeSqlite.load(neon)
        val sheet = BenchSheet(context, tag, "eyko108-r4-${if (neon) "neon" else "noneon"}", args.getString("commit") ?: "unknown", TestVectors.label("real"))
        val queries = TestVectors.queries("real", 512, queryCount + 1)
        for (n in sizes) {
            val name = "eyko108_sweep_$n.db"
            val (db, openMs) = open(context, name)
            val file: File = context.getDatabasePath(name)
            try {
                exec(db, "CREATE VIRTUAL TABLE v USING vec0(embedding float[512])")
                val top = exactTop(queries.drop(1))
                val insertMs = timeMs { insertAndScore(db, "v", 512, n, 31L, queries.drop(1), top) }
                val fileMb = file.length() / 1e6
                Log.i(tag, "n=$n ($method) open %.1f ms, insert+exact %.0f ms, file %.1f MB".format(Locale.ROOT, openMs, insertMs, fileMb))

                val query = NativeSqlite.nativePrepare(db, "SELECT rowid FROM v WHERE embedding MATCH ?1 ORDER BY distance LIMIT $topK")
                check(query != 0L) { "prepare failed: ${NativeSqlite.nativeErrmsg(db)}" }
                try {
                    fun search(q: FloatArray): List<Long> {
                        NativeSqlite.nativeReset(query)
                        NativeSqlite.nativeBindBlob(query, 1, TestVectors.toBlob(q))
                        val ids = ArrayList<Long>(topK)
                        while (NativeSqlite.nativeStep(query) == NativeSqlite.ROW) ids += NativeSqlite.nativeColumnLong(query, 0)
                        return ids
                    }
                    search(queries[0]) // warm-up
                    val same = queries.drop(1).indices.sumOf { i -> search(queries[i + 1]).toSet().intersect(top[i].toSet()).size }
                    val recall = "recall@$topK %.4f (%d of %d); open_ms=%.1f; insert_ms=%.0f".format(Locale.ROOT, same.toDouble() / (queryCount * topK), same, queryCount * topK, openMs, insertMs)
                    Log.i(tag, "n=$n ($method) $recall")
                    for (run in 1..runs) {
                        val tempStart = battery(context).first
                        sheet.row(method, 512, n, "$run", queries.drop(1).map { q -> timeMs { search(q) } }, fileMb, tempStart, recall)
                    }
                } finally {
                    NativeSqlite.nativeFinalize(query)
                }
            } finally {
                NativeSqlite.nativeClose(db)
                file.delete()
            }
        }
        sheet.done()
    }

    /** Memory with all three tables (image 512, text 384, audio-sized 512), n rows each, in vec0 tables. */
    @Test
    fun memoryAllTables() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "5k,20k,50k,100k").split(",").map { parseSize(it) }
        NativeSqlite.load(neon)
        val sheet = BenchSheet(context, tag, "eyko108-r4-memory-${if (neon) "neon" else "noneon"}", args.getString("commit") ?: "unknown", TestVectors.label("real"))
        val tables = listOf(Triple("image_vec", 512, 31L), Triple("text_vec", 384, 32L), Triple("audio_vec", 512, 33L))
        for (n in sizes) {
            val name = "eyko108_memory_$n.db"
            val (db, openMs) = open(context, name)
            val file: File = context.getDatabasePath(name)
            try {
                val before = settle()
                var built = 0
                var failed = ""
                for ((table, size, seed) in tables) {
                    try {
                        exec(db, "CREATE VIRTUAL TABLE $table USING vec0(embedding float[$size])")
                        insertAndScore(db, table, size, n, seed, emptyList(), emptyList())
                        val q = NativeSqlite.nativePrepare(db, "SELECT rowid FROM $table WHERE embedding MATCH ?1 ORDER BY distance LIMIT $topK")
                        NativeSqlite.nativeBindBlob(q, 1, TestVectors.toBlob(TestVectors.queries("real", size, 1)[0]))
                        while (NativeSqlite.nativeStep(q) == NativeSqlite.ROW) Unit
                        NativeSqlite.nativeFinalize(q)
                        built++
                    } catch (e: Throwable) {
                        failed = "${e.javaClass.simpleName} on $table: ${e.message}"
                        break
                    }
                }
                val after = settle()
                val note = "pss_before_mb=%.0f; pss_after_mb=%.0f; native_after_mb=%.0f; java_after_mb=%.0f; tables_built=%d of 3; open_ms=%.1f%s".format(
                    Locale.ROOT, before, after, Debug.getNativeHeapAllocatedSize() / 1e6,
                    (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1e6, built, openMs, if (failed.isEmpty()) "" else "; $failed",
                )
                Log.i(tag, "n=$n ($method) $note")
                sheet.row("memory_$method", tables.sumOf { it.second }, n, "", null, file.length() / 1e6, null, note)
            } finally {
                NativeSqlite.nativeClose(db)
                file.delete()
            }
        }
        sheet.done()
    }

    private fun settle(): Double {
        repeat(2) { Runtime.getRuntime().gc(); System.runFinalization() }
        Thread.sleep(300)
        return Debug.MemoryInfo().also { Debug.getMemoryInfo(it) }.totalPss / 1024.0
    }

    /** Placeholder list: one empty exact-result slot per query; filled by [insertAndScore]. */
    private fun exactTop(queries: List<FloatArray>): List<LongArray> = List(queries.size) { LongArray(topK) }

    /**
     * Inserts n vectors (ids 1..n) from the real-vector stream into vec0 table [table], and in the same
     * pass finds each query's exact top 20 by dot product (unit vectors: the same order as L2),
     * written into [top]. Only the 20 best of each query are kept.
     */
    private fun insertAndScore(db: Long, table: String, size: Int, n: Int, seed: Long, queries: List<FloatArray>, top: List<LongArray>) {
        val next = TestVectors.stream("real", size, seed)
        val best = Array(queries.size) { FloatArray(topK) { Float.NEGATIVE_INFINITY } }
        val bestId = Array(queries.size) { LongArray(topK) }
        exec(db, "BEGIN")
        val insert = NativeSqlite.nativePrepare(db, "INSERT INTO $table(rowid, embedding) VALUES (?1, ?2)")
        check(insert != 0L) { "prepare failed: ${NativeSqlite.nativeErrmsg(db)}" }
        try {
            for (id in 1..n) {
                val v = next()
                NativeSqlite.nativeReset(insert)
                NativeSqlite.nativeBindLong(insert, 1, id.toLong())
                NativeSqlite.nativeBindBlob(insert, 2, TestVectors.toBlob(v))
                val rc = NativeSqlite.nativeStep(insert)
                check(rc == NativeSqlite.DONE) { "insert failed ($rc): ${NativeSqlite.nativeErrmsg(db)}" }
                for (qi in queries.indices) {
                    val q = queries[qi]
                    var s = 0f
                    for (i in 0 until size) s += v[i] * q[i]
                    val b = best[qi]
                    var worst = 0
                    for (k in 1 until topK) if (b[k] < b[worst]) worst = k
                    if (s > b[worst]) { b[worst] = s; bestId[qi][worst] = id.toLong() }
                }
            }
        } finally {
            NativeSqlite.nativeFinalize(insert)
        }
        exec(db, "COMMIT")
        for (qi in queries.indices) bestId[qi].copyInto(top[qi])
    }
}
