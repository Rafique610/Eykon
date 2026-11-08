package com.eykon.memory.spike

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.os.Build
import android.os.Debug
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import org.junit.runner.RunWith
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale

/**
 * EYKO-31 spike (throwaway): can the phone's SQLite use sqlite-vec, and how fast is the
 * plain alternative (float32 BLOB column + brute-force dot product)?
 * Results go to logcat under the tag EYKO31, and (EYKO-90 / EYKO-100) the sweep and the memory
 * test also write a CSV to the app's files/results folder. Run with `task spike-android-vectors`
 * or the phone kit commands. Vectors, CSV and battery helpers: BenchKit.kt.
 */
@RunWith(AndroidJUnit4::class)
class VectorStorageSpikeTest {

    private val tag = "EYKO31"
    private val dim = 512
    private val queryCount = 20
    private val topK = 20

    /** The app's search (VideoVectors.knn before EYKO-102): dot product per row, then sort every row. */
    private fun topK(matrix: FloatArray, rows: Int, query: FloatArray): List<Int> {
        val scores = FloatArray(rows)
        for (r in 0 until rows) {
            var sum = 0f
            val base = r * dim
            for (i in 0 until dim) sum += matrix[base + i] * query[i]
            scores[r] = sum
        }
        return (0 until rows).sortedByDescending { scores[it] }.take(topK)
    }

    /**
     * EYKO-100: the same answer written for speed, to tell the chip from our code (B5): four
     * running sums per row, and a [topK]-slot min-heap instead of sorting every row.
     */
    private fun topKFast(matrix: FloatArray, rows: Int, query: FloatArray): List<Int> {
        val ids = IntArray(topK)
        val best = FloatArray(topK)
        var size = 0
        for (r in 0 until rows) {
            val base = r * dim
            var s0 = 0f
            var s1 = 0f
            var s2 = 0f
            var s3 = 0f
            var i = 0
            while (i < dim) {
                s0 += matrix[base + i] * query[i]
                s1 += matrix[base + i + 1] * query[i + 1]
                s2 += matrix[base + i + 2] * query[i + 2]
                s3 += matrix[base + i + 3] * query[i + 3]
                i += 4
            }
            val score = (s0 + s1) + (s2 + s3)
            if (size < topK) {
                var c = size++
                while (c > 0 && best[(c - 1) / 2] > score) { // sift up
                    best[c] = best[(c - 1) / 2]; ids[c] = ids[(c - 1) / 2]; c = (c - 1) / 2
                }
                best[c] = score; ids[c] = r
            } else if (score > best[0]) {
                var c = 0
                while (true) { // sift down
                    var child = 2 * c + 1
                    if (child >= topK) break
                    if (child + 1 < topK && best[child + 1] < best[child]) child++
                    if (best[child] >= score) break
                    best[c] = best[child]; ids[c] = ids[child]; c = child
                }
                best[c] = score; ids[c] = r
            }
        }
        return (0 until size).sortedByDescending { best[it] }.map { ids[it] }
    }

    private fun readMatrix(db: SQLiteDatabase, table: String, rows: Int, size: Int): FloatArray {
        val matrix = FloatArray(rows * size)
        db.rawQuery("SELECT embedding FROM $table ORDER BY rowid", null).use { cursor ->
            var r = 0
            while (cursor.moveToNext()) {
                ByteBuffer.wrap(cursor.getBlob(0)).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(matrix, r * size, size)
                r++
            }
        }
        return matrix
    }

    private fun insert(db: SQLiteDatabase, table: String, n: Int, next: () -> FloatArray) {
        db.execSQL("CREATE TABLE $table (id INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
        db.beginTransaction()
        val statement = db.compileStatement("INSERT INTO $table VALUES (?, ?)")
        for (i in 0 until n) {
            statement.bindLong(1, i.toLong())
            statement.bindBlob(2, TestVectors.toBlob(next()))
            statement.executeInsert()
        }
        db.setTransactionSuccessful()
        db.endTransaction()
    }

    @Test
    fun sqliteVecOnThePlatformSqlite() {
        val db = SQLiteDatabase.create(null)
        try {
            db.rawQuery("SELECT sqlite_version()", null).use {
                it.moveToFirst()
                Log.i(tag, "device ${Build.MANUFACTURER} ${Build.MODEL}, Android ${Build.VERSION.RELEASE}, platform sqlite ${it.getString(0)}")
            }
            try {
                db.execSQL("CREATE VIRTUAL TABLE v USING vec0(embedding float[$dim])")
                Log.i(tag, "option 1: vec0 table created on the platform SQLite (unexpected)")
            } catch (e: Exception) {
                Log.i(tag, "option 1: CREATE VIRTUAL TABLE ... USING vec0 failed: ${e.message}")
            }
            try {
                db.rawQuery("SELECT load_extension('vec0')", null).use { it.moveToFirst() }
                Log.i(tag, "option 1: load_extension('vec0') succeeded (unexpected)")
            } catch (e: Exception) {
                Log.i(tag, "option 1: load_extension('vec0') failed: ${e.message}")
            }
            // EYKO-100 (A2): is it sqlite-vec, or does the platform block every loadable extension?
            try {
                db.rawQuery("SELECT load_extension('eyko_no_such_extension')", null).use { it.moveToFirst() }
                Log.i(tag, "any extension: load_extension of a made-up name succeeded (unexpected)")
            } catch (e: Exception) {
                Log.i(tag, "any extension: load_extension('eyko_no_such_extension') failed: ${e.message}")
            }
            for (module in listOf("fts5", "fts4", "rtree")) {
                val columns = if (module == "rtree") "id, x0, x1" else "body"
                try {
                    db.execSQL("CREATE VIRTUAL TABLE t_$module USING $module($columns)")
                    Log.i(tag, "built-in module: $module works (compiled into the platform SQLite)")
                } catch (e: Exception) {
                    Log.i(tag, "built-in module: $module failed: ${e.message}")
                }
            }
            db.rawQuery("PRAGMA compile_options", null).use { c ->
                val options = generateSequence { if (c.moveToNext()) c.getString(0) else null }.toList()
                val relevant = options.filter { "EXTENSION" in it || "FTS" in it || "RTREE" in it }
                Log.i(tag, "compile options (extension / fts / rtree): ${relevant.ifEmpty { listOf("none listed") }}")
            }
        } finally {
            db.close()
        }
    }

    /**
     * EYKO-90 sweep: BLOB column + brute-force dot product at each size, 1 warm-up query thrown
     * away, then [queryCount] queries x `runs`. One CSV row per (method, size, run) in the shared
     * format, written as it goes so a crash or out-of-memory keeps the rows before it.
     * Arguments (`-e name value`): sizes (default 5k,20k; e.g. 1k,5k,20k,50k,100k,300k),
     * runs (default 5), diskMax (largest size for the read-from-SQLite method, default 20k:
     * it reads the whole table per query), source (random, default, or real: EYKO-100),
     * commit (the kit's commit hash).
     * Methods: blob_disk_dot, blob_memory_dot (the app's loop) and blob_memory_fast (EYKO-100).
     */
    @Test
    fun blobColumnWithBruteForceSearch() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "5k,20k").split(",").map { parseSize(it) }
        val runs = args.getString("runs")?.toInt() ?: 5
        val diskMax = parseSize(args.getString("diskMax") ?: "20k")
        val source = args.getString("source") ?: "random"
        val sheet = BenchSheet(context, tag, if (source == "real") "eyko100-sweep-real" else "eyko90", args.getString("commit") ?: "unknown", TestVectors.label(source))
        Log.i(tag, "sweep: sizes $sizes, runs $runs, diskMax $diskMax, source $source")

        val queries = TestVectors.queries(source, dim, queryCount + 1) // the first one is the warm-up
        for (n in sizes) {
            val file = context.getDatabasePath("eyko90_sweep_$n.db")
            file.parentFile?.mkdirs()
            file.delete()
            val db = SQLiteDatabase.openOrCreateDatabase(file, null)
            try {
                val insertMs = timeMs { insert(db, "image_vec", n, TestVectors.stream(source, dim, 31)) }
                val fileMb = file.length() / 1e6
                Log.i(tag, "n=$n insert all: %.0f ms, file %.1f MB".format(Locale.ROOT, insertMs, fileMb))

                if (n <= diskMax) {
                    try {
                        topK(readMatrix(db, "image_vec", n, dim), n, queries[0])
                        for (run in 1..runs) {
                            val tempStart = battery(context).first
                            sheet.row("blob_disk_dot", dim, n, "$run", queries.drop(1).map { q -> timeMs { topK(readMatrix(db, "image_vec", n, dim), n, q) } }, fileMb, tempStart)
                        }
                    } catch (e: OutOfMemoryError) {
                        sheet.row("blob_disk_dot", dim, n, "", null, fileMb, null, "OutOfMemoryError: ${e.message}")
                    }
                } else {
                    sheet.row("blob_disk_dot", dim, n, "", null, fileMb, null, "skipped: over diskMax $diskMax")
                }

                try {
                    val matrix = readMatrix(db, "image_vec", n, dim)
                    topK(matrix, n, queries[0])
                    for (run in 1..runs) {
                        val tempStart = battery(context).first
                        sheet.row("blob_memory_dot", dim, n, "$run", queries.drop(1).map { q -> timeMs { topK(matrix, n, q) } }, fileMb, tempStart)
                    }
                    val same = queries.drop(1).sumOf { q -> topK(matrix, n, q).toSet().intersect(topKFast(matrix, n, q).toSet()).size }
                    val check = "fast top-$topK equals the app's: $same of ${queryCount * topK}"
                    Log.i(tag, "n=$n $check")
                    topKFast(matrix, n, queries[0])
                    for (run in 1..runs) {
                        val tempStart = battery(context).first
                        sheet.row("blob_memory_fast", dim, n, "$run", queries.drop(1).map { q -> timeMs { topKFast(matrix, n, q) } }, fileMb, tempStart, check)
                    }
                } catch (e: OutOfMemoryError) {
                    sheet.row("blob_memory_dot", dim, n, "", null, fileMb, null, "OutOfMemoryError: ${e.message}")
                }
            } finally {
                db.close()
                file.delete()
            }
        }
        sheet.done()
    }

    /**
     * EYKO-100 (B4): honest memory. Three tables as the app has them (image 512, text 384 and an
     * audio-sized 512, the same n rows each: the worst case) are loaded together the way the app
     * loads them. Total PSS (Debug.getMemoryInfo) is read after a GC before and after loading.
     * Arguments: sizes (default 5k,20k,50k,100k), source (default real), commit.
     */
    @Test
    fun memoryWithAllThreeTables() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "5k,20k,50k,100k").split(",").map { parseSize(it) }
        val source = args.getString("source") ?: "real"
        val sheet = BenchSheet(context, tag, "eyko100-memory", args.getString("commit") ?: "unknown", TestVectors.label(source))
        val tables = listOf("image_vec" to 512, "text_vec" to 384, "audio_vec" to 512)
        for (n in sizes) {
            val file = context.getDatabasePath("eyko100_memory_$n.db")
            file.parentFile?.mkdirs()
            file.delete()
            val db = SQLiteDatabase.openOrCreateDatabase(file, null)
            try {
                tables.forEachIndexed { i, (table, size) -> insert(db, table, n, TestVectors.stream(source, size, 31L + i)) }
                val fileMb = file.length() / 1e6
                val pssBefore = pssMb()
                val loaded = ArrayList<FloatArray>()
                var failed = ""
                for ((table, size) in tables) {
                    try {
                        loaded += readMatrix(db, table, n, size)
                    } catch (e: OutOfMemoryError) {
                        failed = "OutOfMemoryError while loading $table: ${e.message}"
                        break
                    }
                }
                val pssAfter = pssMb()
                val vectorsMb = loaded.sumOf { it.size } * 4 / 1e6 // also keeps the tables alive until after the reading
                Log.i(tag, "n=$n all tables: PSS %.0f -> %.0f MB, vectors held %.0f MB %s".format(Locale.ROOT, pssBefore, pssAfter, vectorsMb, failed))
                sheet.row(
                    "memory_all_tables", tables.sumOf { it.second }, n, "", null, fileMb, null,
                    "pss_before_mb=%.0f; pss_after_mb=%.0f; vectors_held_mb=%.0f; tables_loaded=%d of 3%s".format(
                        Locale.ROOT, pssBefore, pssAfter, vectorsMb, loaded.size, if (failed.isEmpty()) "" else "; $failed",
                    ),
                )
            } finally {
                db.close()
                file.delete()
            }
        }
        sheet.done()
    }

    private fun pssMb(): Double {
        repeat(2) { Runtime.getRuntime().gc(); System.runFinalization() }
        Thread.sleep(300)
        return Debug.MemoryInfo().also { Debug.getMemoryInfo(it) }.totalPss / 1024.0
    }
}
