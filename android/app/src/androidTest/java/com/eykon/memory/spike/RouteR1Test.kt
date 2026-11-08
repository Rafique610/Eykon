package com.eykon.memory.spike

import android.content.Context
import android.util.Log
import androidx.sqlite.SQLiteConnection
import androidx.sqlite.SQLiteStatement
import androidx.sqlite.driver.bundled.BundledSQLiteDriver
import androidx.sqlite.driver.bundled.SQLITE_OPEN_CREATE
import androidx.sqlite.driver.bundled.SQLITE_OPEN_FULLMUTEX
import androidx.sqlite.driver.bundled.SQLITE_OPEN_READWRITE
import androidx.sqlite.execSQL
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.Locale

/**
 * EYKO-105, route R1 (throwaway): sqlite-vec loaded into Google's bundled SQLite
 * (androidx.sqlite:sqlite-bundled, BundledSQLiteDriver.addExtension), the app's own SQLite untouched.
 * The plugin is our own build from EYKO-104 (test assets "neon" / "no-neon", copied into the app's
 * files first, SHA256 logged). Same vectors, queries and CSV format as EYKO-100. Tag EYKO31.
 */
@RunWith(AndroidJUnit4::class)
class RouteR1Test {

    private val tag = "EYKO31"
    private val dim = 512
    private val queryCount = 20
    private val topK = 20
    private val source = "real"

    private fun open(pluginPath: String, file: File): SQLiteConnection =
        BundledSQLiteDriver().apply { addExtension(pluginPath, "sqlite3_vec_init") }
            .open(file.absolutePath, SQLITE_OPEN_READWRITE or SQLITE_OPEN_CREATE or SQLITE_OPEN_FULLMUTEX)

    private fun SQLiteConnection.texts(sql: String, columns: Int): List<String> =
        prepare(sql).closing { st -> st.step(); List(columns) { st.getText(it) } }

    /** One vec0 table with the default L2 metric (EYKO-104: NEON speeds up L2, not cosine); vectors are unit length. */
    private fun fill(db: SQLiteConnection, table: String, size: Int, n: Int, next: () -> FloatArray, keep: FloatArray?) {
        db.execSQL("CREATE VIRTUAL TABLE $table USING vec0(embedding float[$size])")
        db.execSQL("BEGIN")
        db.prepare("INSERT INTO $table(rowid, embedding) VALUES (?, ?)").closing { st ->
            for (i in 0 until n) {
                val v = next()
                keep?.let { System.arraycopy(v, 0, it, i * size, size) }
                st.bindLong(1, i.toLong())
                st.bindBlob(2, TestVectors.toBlob(v))
                st.step()
                st.reset()
            }
        }
        db.execSQL("COMMIT")
    }

    private fun knnStatement(db: SQLiteConnection, table: String): SQLiteStatement =
        db.prepare("SELECT rowid FROM $table WHERE embedding MATCH ? AND k = $topK ORDER BY distance")

    private fun knn(st: SQLiteStatement, query: FloatArray): List<Int> {
        st.reset()
        st.bindBlob(1, TestVectors.toBlob(query))
        return buildList { while (st.step()) add(st.getLong(0).toInt()) }
    }

    /**
     * Load check, then the shared sweep: per size, `sqlite_vec_bundled` (vec0 knn, top 20) against
     * `blob_memory_fast` (the exact in-memory search) on the same vectors and queries, 1 warm-up +
     * 20 queries x `runs`, with recall@20. At `neonSizes` the no-NEON build is timed on the same file.
     * Arguments: sizes (default 1k,5k,20k,50k,100k), runs (5), neonSizes (20k,100k), commit.
     */
    @Test
    fun loadAndSweep() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "1k,5k,20k,50k,100k").split(",").map { parseSize(it) }
        val runs = args.getString("runs")?.toInt() ?: 5
        val neonSizes = (args.getString("neonSizes") ?: "20k,100k").split(",").map { parseSize(it) }.toSet()
        val (neon, neonSha) = sqliteVecPlugin(context, "neon")
        val (plain, plainSha) = sqliteVecPlugin(context, "no-neon")
        Log.i(tag, "R1 plugin neon: $neon sha256 $neonSha")
        Log.i(tag, "R1 plugin no-neon: $plain sha256 $plainSha")

        val probe = context.getDatabasePath("eyko105_probe.db").apply { parentFile?.mkdirs(); delete() }
        var db: SQLiteConnection? = null
        val openMs = timeMs { db = open(neon, probe) }
        val version = db!!.closing { c ->
            val v = c.texts("SELECT sqlite_version(), vec_version(), vec_debug()", 3)
            Log.i(tag, "R1 loads: sqlite ${v[0]}, vec_version ${v[1]}, first open with plugin %.1f ms".format(Locale.ROOT, openMs))
            Log.i(tag, "R1 vec_debug: ${v[2].replace("\n", " | ")}")
            c.execSQL("CREATE VIRTUAL TABLE t USING fts5(body)")
            c.execSQL("INSERT INTO t VALUES ('where did i put my keys')")
            Log.i(tag, "R1 fts5 works: bm25 = ${c.texts("SELECT bm25(t) FROM t WHERE t MATCH 'keys'", 1)[0]}")
            v
        }
        probe.delete()

        val sheet = BenchSheet(context, tag, "eyko105-route-r1", args.getString("commit") ?: "unknown", TestVectors.label(source), version[0])
        val queries = TestVectors.queries(source, dim, queryCount + 1) // the first one is the warm-up
        // the exact reference, allocated once at the largest size (a new array per size ran out of Java heap at 100k)
        val matrix = FloatArray(sizes.max() * dim)
        for (n in sizes) {
            val file = context.getDatabasePath("eyko105_sweep_$n.db").apply { delete() }
            try {
                open(neon, file).closing { c ->
                    val insertMs = timeMs { fill(c, "image_vec", dim, n, TestVectors.stream(source, dim, 31), matrix) }
                    val fileMb = file.length() / 1e6
                    Log.i(tag, "n=$n vec0 insert all: %.0f ms, file %.1f MB".format(Locale.ROOT, insertMs, fileMb))
                    val exact = queries.drop(1).map { exactTopK(matrix, n, dim, it, topK) }
                    knnStatement(c, "image_vec").closing { st ->
                        val hits = queries.drop(1).mapIndexed { q, query -> knn(st, query).toSet().intersect(exact[q].toSet()).size }.sum()
                        val recall = "recall@$topK %.4f (%d of %d) against blob_memory_fast".format(Locale.ROOT, hits / (queryCount * topK.toDouble()), hits, queryCount * topK)
                        Log.i(tag, "n=$n sqlite_vec_bundled $recall")
                        knn(st, queries[0])
                        for (run in 1..runs) {
                            val temp = battery(context).first
                            sheet.row("sqlite_vec_bundled", dim, n, "$run", queries.drop(1).map { q -> timeMs { knn(st, q) } }, fileMb, temp, "$recall; ${version[2].lines().last()}")
                        }
                    }
                    exactTopK(matrix, n, dim, queries[0], topK)
                    for (run in 1..runs) {
                        val temp = battery(context).first
                        sheet.row("blob_memory_fast", dim, n, "$run", queries.drop(1).map { q -> timeMs { exactTopK(matrix, n, dim, q, topK) } }, fileMb, temp)
                    }
                }
                if (n in neonSizes) open(plain, file).closing { c ->
                    val build = c.texts("SELECT vec_debug()", 1)[0].lines().last()
                    knnStatement(c, "image_vec").closing { st ->
                        knn(st, queries[0])
                        for (run in 1..runs) {
                            val temp = battery(context).first
                            sheet.row("sqlite_vec_bundled_noneon", dim, n, "$run", queries.drop(1).map { q -> timeMs { knn(st, q) } }, file.length() / 1e6, temp, build)
                        }
                    }
                }
            } catch (e: Throwable) {
                sheet.row("sqlite_vec_bundled", dim, n, "", null, file.length() / 1e6, null, "${e.javaClass.simpleName}: ${e.message}")
                if (e is OutOfMemoryError) break
            } finally {
                file.delete()
            }
        }
        sheet.done()
    }

    /**
     * B4 with vec0: three tables (image 512, text 384, audio-sized 512, n rows each) in one
     * database, one knn query on each, total PSS before and after. Compare with EYKO-100's
     * memory_all_tables (BLOBs loaded into the Java heap: out of memory at 50k).
     * Arguments: sizes (default 20k,50k,100k), commit.
     */
    @Test
    fun memoryWithAllThreeTables() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "20k,50k,100k").split(",").map { parseSize(it) }
        val neon: String = sqliteVecPlugin(context, "neon").first
        val tables: List<Pair<String, Int>> = listOf("image_vec" to 512, "text_vec" to 384, "audio_vec" to 512)
        val queries: Map<String, FloatArray> = tables.associate { it.first to TestVectors.queries(source, it.second, 1)[0] }
        val probe = context.getDatabasePath("eyko105_probe.db").apply { parentFile?.mkdirs(); delete() }
        val sqlite: String = open(neon, probe).closing { c: SQLiteConnection -> c.texts("SELECT sqlite_version()", 1)[0] }
        probe.delete()
        val sheet = BenchSheet(context, tag, "eyko105-route-r1-memory", args.getString("commit") ?: "unknown", TestVectors.label(source), sqlite)
        for (n in sizes) {
            val file = context.getDatabasePath("eyko105_memory_$n.db").apply { delete() }
            try {
                open(neon, file).closing { c: SQLiteConnection ->
                    tables.forEachIndexed { i, t -> fill(c, t.first, t.second, n, TestVectors.stream(source, t.second, 31L + i), null) }
                    val pssBefore = pssMb()
                    val found = tables.sumOf { t -> knnStatement(c, t.first).closing { knn(it, queries.getValue(t.first)).size } }
                    val pssAfter = pssMb()
                    val heapMb = Runtime.getRuntime().let { (it.totalMemory() - it.freeMemory()) / 1e6 }
                    Log.i(tag, "n=$n vec0 all tables: PSS %.0f -> %.0f MB, java heap %.0f MB, %d hits".format(Locale.ROOT, pssBefore, pssAfter, heapMb, found))
                    sheet.row(
                        "memory_all_tables_vec0", tables.sumOf { it.second }, n, "", null, file.length() / 1e6, null,
                        "pss_before_mb=%.0f; pss_after_mb=%.0f; java_heap_mb=%.0f; tables_searched=3 of 3; hits=%d".format(Locale.ROOT, pssBefore, pssAfter, heapMb, found),
                    )
                }
            } catch (e: Throwable) {
                sheet.row("memory_all_tables_vec0", tables.sumOf { it.second }, n, "", null, file.length() / 1e6, null, "${e.javaClass.simpleName}: ${e.message}")
            } finally {
                file.delete()
            }
        }
        sheet.done()
    }
}

/** `use` for the bundled driver's AutoCloseable connections and statements. */
internal inline fun <T : AutoCloseable, R> T.closing(block: (T) -> R): R = try { block(this) } finally { close() }
