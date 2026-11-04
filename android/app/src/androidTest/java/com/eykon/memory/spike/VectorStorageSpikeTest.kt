package com.eykon.memory.spike

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.database.sqlite.SQLiteDatabase
import android.os.BatteryManager
import android.os.Build
import android.os.Debug
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.Random
import kotlin.math.ceil
import kotlin.math.sqrt

/**
 * EYKO-31 spike (throwaway): can the phone's SQLite use sqlite-vec, and how fast is the
 * plain alternative (float32 BLOB column + brute-force dot product)?
 * Results go to logcat under the tag EYKO31, and (EYKO-90 / EYKO-100) the sweep and the memory
 * test also write a CSV to the app's files/results folder. Run with `task spike-android-vectors`
 * or the phone kit commands.
 */
@RunWith(AndroidJUnit4::class)
class VectorStorageSpikeTest {

    private val tag = "EYKO31"
    private val dim = 512
    private val queryCount = 20
    private val topK = 20

    private fun unit(v: FloatArray): FloatArray {
        val norm = sqrt(v.fold(0.0) { acc, x -> acc + x * x }).toFloat()
        for (i in v.indices) v[i] /= norm
        return v
    }

    /**
     * Endless unit vectors of [size] numbers. "random": Gaussian, fixed seed. "real" (EYKO-100):
     * the vectors of our own clips in the test assets (90 per table), first as they are, then
     * repeated with small noise (0.01 per number, about 0.97 cosine to the original).
     */
    private fun vectors(source: String, size: Int, seed: Long): () -> FloatArray {
        val random = Random(seed)
        if (source != "real") return { unit(FloatArray(size) { random.nextGaussian().toFloat() }) }
        val base = realVectors(size)
        var i = 0
        return {
            val b = base[i % base.size]
            i++
            if (i <= base.size) b.copyOf() else unit(FloatArray(size) { b[it] + 0.01f * random.nextGaussian().toFloat() })
        }
    }

    private fun realVectors(size: Int): List<FloatArray> {
        val name = if (size == 512) "vectors/own_image_512.f32" else "vectors/own_text_384.f32"
        val bytes = InstrumentationRegistry.getInstrumentation().context.assets.open(name).use { it.readBytes() }
        val floats = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
        return List(floats.remaining() / size) { FloatArray(size).also { v -> floats.get(v) } }
    }

    private fun sourceLabel(source: String) = if (source == "real") "real_own_clips_90+noise" else "random_unit_seed31"

    private fun toBlob(v: FloatArray): ByteArray =
        ByteBuffer.allocate(v.size * 4).order(ByteOrder.LITTLE_ENDIAN).apply { asFloatBuffer().put(v) }.array()

    /** The app's search (VideoVectors.knn): dot product per row, then sort every row. */
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
            statement.bindBlob(2, toBlob(next()))
            statement.executeInsert()
        }
        db.setTransactionSuccessful()
        db.endTransaction()
    }

    private fun timeMs(block: () -> Unit): Double {
        val start = System.nanoTime()
        block()
        return (System.nanoTime() - start) / 1e6
    }

    private fun report(label: String, times: List<Double>) {
        val sorted = times.sorted()
        Log.i(tag, "%s: median %.2f ms, worst %.2f ms".format(label, sorted[sorted.size / 2], sorted.last()))
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
        val sheet = Sheet(context, if (source == "real") "eyko100-sweep-real" else "eyko90", args.getString("commit") ?: "unknown", sourceLabel(source))
        Log.i(tag, "sweep: sizes $sizes, runs $runs, diskMax $diskMax, source $source")

        // The first query is the warm-up. Random queries are the same ones EYKO-90 used (seed 90).
        val queries = if (source == "real") realQueries() else vectors(source, dim, 90).let { next -> List(queryCount + 1) { next() } }
        for (n in sizes) {
            val file = context.getDatabasePath("eyko90_sweep_$n.db")
            file.parentFile?.mkdirs()
            file.delete()
            val db = SQLiteDatabase.openOrCreateDatabase(file, null)
            try {
                val insertMs = timeMs { insert(db, "image_vec", n, vectors(source, dim, 31)) }
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

    /** Real queries: our own frames with more noise (0.05 per number), so they are near, not equal to, stored rows. */
    private fun realQueries(): List<FloatArray> {
        val base = realVectors(dim)
        val random = Random(90)
        return List(queryCount + 1) { q -> unit(FloatArray(dim) { base[(q * 7) % base.size][it] + 0.05f * random.nextGaussian().toFloat() }) }
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
        val sheet = Sheet(context, "eyko100-memory", args.getString("commit") ?: "unknown", sourceLabel(source))
        val tables = listOf("image_vec" to 512, "text_vec" to 384, "audio_vec" to 512)
        for (n in sizes) {
            val file = context.getDatabasePath("eyko100_memory_$n.db")
            file.parentFile?.mkdirs()
            file.delete()
            val db = SQLiteDatabase.openOrCreateDatabase(file, null)
            try {
                tables.forEachIndexed { i, (table, size) -> insert(db, table, n, vectors(source, size, 31L + i)) }
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

    /** Prints the device sheet and writes the CSV rows (shared format, EYKO-90). */
    private inner class Sheet(private val context: Context, prefix: String, private val commit: String, private val source: String) {
        private val sqlite = SQLiteDatabase.create(null).use { db ->
            db.rawQuery("SELECT sqlite_version()", null).use { it.moveToFirst(); it.getString(0) }
        }
        private val device = "${Build.MANUFACTURER} ${Build.MODEL}"
        private val date = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(Date())
        private val csv: File

        init {
            val ram = ActivityManager.MemoryInfo().also { context.getSystemService(ActivityManager::class.java).getMemoryInfo(it) }
            Log.i(tag, "device sheet: $device, Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}), sqlite $sqlite, commit $commit, date $date")
            Log.i(
                tag,
                "device sheet: RAM %.1f GB, java heap limit %.0f MB, free storage %.1f GB, vectors %s".format(
                    Locale.ROOT, ram.totalMem / 1e9, Runtime.getRuntime().maxMemory() / 1e6, context.filesDir.usableSpace / 1e9, source,
                ),
            )
            val outDir = context.getExternalFilesDir("results")!!.apply { mkdirs() }
            csv = File(outDir, "$prefix-${Build.MODEL.replace(Regex("[^A-Za-z0-9]+"), "_")}-${SimpleDateFormat("yyyyMMdd-HHmm", Locale.ROOT).format(Date())}.csv")
            csv.writeText(CSV_HEADER + "\n")
        }

        fun row(method: String, dims: Int, n: Int, run: String, times: List<Double>?, fileMb: Double, tempStart: Double?, note: String = "") {
            val runtime = Runtime.getRuntime()
            val battery = battery(context)
            val stats = times?.sorted()?.let { s ->
                listOf(s[s.size / 2], s[ceil(0.95 * s.size).toInt() - 1], s.last()).joinToString(",") { "%.2f".format(Locale.ROOT, it) }
            } ?: ",,"
            csv.appendText(
                listOf(
                    device, Build.VERSION.RELEASE, sqlite, commit, date, method, dims, n, run, stats,
                    "%.0f".format(Locale.ROOT, Debug.getPss() / 1024.0),
                    "%.0f".format(Locale.ROOT, (runtime.totalMemory() - runtime.freeMemory()) / 1e6),
                    "%.1f".format(Locale.ROOT, fileMb),
                    tempStart?.let { "%.1f".format(Locale.ROOT, it) } ?: "",
                    "%.1f".format(Locale.ROOT, battery.first), battery.second, source, note.replace(",", ";"),
                ).joinToString(",") + "\n",
            )
            if (times != null) report("n=$n $method run $run", times) else if (note.isNotEmpty()) Log.i(tag, "n=$n $method: $note")
        }

        fun done() {
            Log.i(tag, "csv written: ${csv.absolutePath}")
            Log.i(tag, "pull it with: adb pull ${csv.absolutePath}")
        }
    }

    private fun parseSize(text: String): Int = text.trim().lowercase(Locale.ROOT).let {
        if (it.endsWith("k")) it.dropLast(1).toInt() * 1_000 else it.toInt()
    }

    /** (battery temperature in °C, battery level in %), from the sticky battery broadcast. */
    private fun battery(context: Context): Pair<Double, Int> {
        val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))!!
        val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) * 100 / intent.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
        return intent.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0) / 10.0 to level
    }

    private companion object {
        /** The shared laptop/phone format from EYKO-90, plus a last `note` column for skips and failures. */
        const val CSV_HEADER = "device,android,sqlite_version,commit,date,method,dim,n,run,median_ms,p95_ms,worst_ms," +
            "pss_mb,heap_mb,file_mb,temp_c_start,temp_c_end,battery_pct,source_vectors,note"
    }
}
