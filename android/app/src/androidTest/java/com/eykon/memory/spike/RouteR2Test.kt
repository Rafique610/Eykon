package com.eykon.memory.spike

import android.content.Context
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import io.requery.android.database.sqlite.SQLiteCustomExtension
import io.requery.android.database.sqlite.SQLiteDatabase
import io.requery.android.database.sqlite.SQLiteDatabaseConfiguration
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.Locale

/**
 * EYKO-106, route R2 (throwaway): sqlite-vec loaded into requery's SQLite (sqlite-android 3.49.0,
 * SQLiteCustomExtension), the app's own SQLite untouched. Same plugin files (EYKO-104), vectors,
 * queries and CSV format as R1 (RouteR1Test), so the two compare on the same phone. Tag EYKO31.
 */
@RunWith(AndroidJUnit4::class)
class RouteR2Test {

    private val tag = "EYKO31"
    private val dim = 512
    private val queryCount = 20
    private val topK = 20
    private val source = "real"

    private fun open(pluginPath: String, file: File): SQLiteDatabase {
        val config = SQLiteDatabaseConfiguration(file.absolutePath, SQLiteDatabase.CREATE_IF_NECESSARY or SQLiteDatabase.OPEN_READWRITE)
        config.customExtensions.add(SQLiteCustomExtension(pluginPath, "sqlite3_vec_init"))
        return SQLiteDatabase.openDatabase(config, null, null)
    }

    private fun SQLiteDatabase.texts(sql: String, columns: Int): List<String> =
        rawQuery(sql, null).use { c -> c.moveToFirst(); List(columns) { c.getString(it) } }

    /** One vec0 table, default L2 metric (EYKO-104: NEON speeds up L2, not cosine); vectors are unit length. */
    private fun fill(db: SQLiteDatabase, table: String, size: Int, n: Int, next: () -> FloatArray, keep: FloatArray?) {
        db.execSQL("CREATE VIRTUAL TABLE $table USING vec0(embedding float[$size])")
        db.beginTransaction()
        db.compileStatement("INSERT INTO $table(rowid, embedding) VALUES (?, ?)").use { st ->
            for (i in 0 until n) {
                val v = next()
                keep?.let { System.arraycopy(v, 0, it, i * size, size) }
                st.bindLong(1, i.toLong())
                st.bindBlob(2, TestVectors.toBlob(v))
                st.executeInsert()
            }
        }
        db.setTransactionSuccessful()
        db.endTransaction()
    }

    private fun knn(db: SQLiteDatabase, table: String, query: FloatArray): List<Int> =
        db.rawQuery("SELECT rowid FROM $table WHERE embedding MATCH ? AND k = $topK ORDER BY distance", arrayOf<Any>(TestVectors.toBlob(query)))
            .use { c -> buildList { while (c.moveToNext()) add(c.getLong(0).toInt()) } }

    /**
     * Load check, then the shared sweep: per size, `sqlite_vec_requery` (vec0 knn, top 20) against
     * `blob_memory_fast` on the same vectors and queries, 1 warm-up + 20 queries x `runs`, with
     * recall@20. At `neonSizes` the no-NEON build is timed on the same file.
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
        Log.i(tag, "R2 plugin neon: $neon sha256 $neonSha")
        Log.i(tag, "R2 plugin no-neon: $plain sha256 $plainSha")

        val probe = context.getDatabasePath("eyko106_probe.db").apply { parentFile?.mkdirs(); delete() }
        var probeDb: SQLiteDatabase? = null
        val openMs = timeMs { probeDb = open(neon, probe) }
        val version = probeDb!!.use { db ->
            val v = db.texts("SELECT sqlite_version(), vec_version(), vec_debug()", 3)
            Log.i(tag, "R2 loads: sqlite ${v[0]}, vec_version ${v[1]}, first open with plugin %.1f ms".format(Locale.ROOT, openMs))
            Log.i(tag, "R2 vec_debug: ${v[2].replace("\n", " | ")}")
            db.execSQL("CREATE VIRTUAL TABLE t USING fts5(body)")
            db.execSQL("INSERT INTO t VALUES ('where did i put my keys')")
            Log.i(tag, "R2 fts5 works: bm25 = ${db.texts("SELECT bm25(t) FROM t WHERE t MATCH 'keys'", 1)[0]}")
            v
        }
        probe.delete()

        val sheet = BenchSheet(context, tag, "eyko106-route-r2", args.getString("commit") ?: "unknown", TestVectors.label(source), version[0])
        val queries = TestVectors.queries(source, dim, queryCount + 1) // the first one is the warm-up
        val matrix = FloatArray(sizes.max() * dim) // the exact reference, allocated once (R1: a new array per size ran out of heap)
        for (n in sizes) {
            val file = context.getDatabasePath("eyko106_sweep_$n.db").apply { delete() }
            try {
                open(neon, file).use { db ->
                    val insertMs = timeMs { fill(db, "image_vec", dim, n, TestVectors.stream(source, dim, 31), matrix) }
                    val fileMb = file.length() / 1e6
                    Log.i(tag, "n=$n vec0 insert all: %.0f ms, file %.1f MB".format(Locale.ROOT, insertMs, fileMb))
                    val exact = queries.drop(1).map { exactTopK(matrix, n, dim, it, topK) }
                    val hits = queries.drop(1).mapIndexed { q, query -> knn(db, "image_vec", query).toSet().intersect(exact[q].toSet()).size }.sum()
                    val recall = "recall@$topK %.4f (%d of %d) against blob_memory_fast".format(Locale.ROOT, hits / (queryCount * topK.toDouble()), hits, queryCount * topK)
                    Log.i(tag, "n=$n sqlite_vec_requery $recall")
                    knn(db, "image_vec", queries[0])
                    for (run in 1..runs) {
                        val temp = battery(context).first
                        sheet.row("sqlite_vec_requery", dim, n, "$run", queries.drop(1).map { q -> timeMs { knn(db, "image_vec", q) } }, fileMb, temp, "$recall; ${version[2].lines().last()}")
                    }
                    exactTopK(matrix, n, dim, queries[0], topK)
                    for (run in 1..runs) {
                        val temp = battery(context).first
                        sheet.row("blob_memory_fast", dim, n, "$run", queries.drop(1).map { q -> timeMs { exactTopK(matrix, n, dim, q, topK) } }, fileMb, temp)
                    }
                }
                if (n in neonSizes) open(plain, file).use { db ->
                    val build = db.texts("SELECT vec_debug()", 1)[0].lines().last()
                    knn(db, "image_vec", queries[0])
                    for (run in 1..runs) {
                        val temp = battery(context).first
                        sheet.row("sqlite_vec_requery_noneon", dim, n, "$run", queries.drop(1).map { q -> timeMs { knn(db, "image_vec", q) } }, file.length() / 1e6, temp, build)
                    }
                }
            } catch (e: Throwable) {
                sheet.row("sqlite_vec_requery", dim, n, "", null, file.length() / 1e6, null, "${e.javaClass.simpleName}: ${e.message}")
                if (e is OutOfMemoryError) break
            } finally {
                file.delete()
            }
        }
        sheet.done()
    }

    /**
     * B4 with vec0 through requery: three tables (image 512, text 384, audio-sized 512, n rows each),
     * one knn query on each, total PSS before and after. Arguments: sizes (default 20k,50k,100k), commit.
     */
    @Test
    fun memoryWithAllThreeTables() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "20k,50k,100k").split(",").map { parseSize(it) }
        val neon = sqliteVecPlugin(context, "neon").first
        val tables = listOf("image_vec" to 512, "text_vec" to 384, "audio_vec" to 512)
        val queries = tables.associate { it.first to TestVectors.queries(source, it.second, 1)[0] }
        val probe = context.getDatabasePath("eyko106_probe.db").apply { parentFile?.mkdirs(); delete() }
        val sqlite = open(neon, probe).use { it.texts("SELECT sqlite_version()", 1)[0] }
        probe.delete()
        val sheet = BenchSheet(context, tag, "eyko106-route-r2-memory", args.getString("commit") ?: "unknown", TestVectors.label(source), sqlite)
        for (n in sizes) {
            val file = context.getDatabasePath("eyko106_memory_$n.db").apply { delete() }
            try {
                open(neon, file).use { db ->
                    tables.forEachIndexed { i, t -> fill(db, t.first, t.second, n, TestVectors.stream(source, t.second, 31L + i), null) }
                    val pssBefore = pssMb()
                    val found = tables.sumOf { t -> knn(db, t.first, queries.getValue(t.first)).size }
                    val pssAfter = pssMb()
                    val heapMb = Runtime.getRuntime().let { (it.totalMemory() - it.freeMemory()) / 1e6 }
                    Log.i(tag, "n=$n vec0 all tables (requery): PSS %.0f -> %.0f MB, java heap %.0f MB, %d hits".format(Locale.ROOT, pssBefore, pssAfter, heapMb, found))
                    sheet.row(
                        "memory_all_tables_vec0_requery", tables.sumOf { it.second }, n, "", null, file.length() / 1e6, null,
                        "pss_before_mb=%.0f; pss_after_mb=%.0f; java_heap_mb=%.0f; tables_searched=3 of 3; hits=%d".format(Locale.ROOT, pssBefore, pssAfter, heapMb, found),
                    )
                }
            } catch (e: Throwable) {
                sheet.row("memory_all_tables_vec0_requery", tables.sumOf { it.second }, n, "", null, file.length() / 1e6, null, "${e.javaClass.simpleName}: ${e.message}")
            } finally {
                file.delete()
            }
        }
        sheet.done()
    }
}
