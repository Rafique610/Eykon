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
 * Results go to logcat under the tag EYKO31, and (EYKO-90) the sweep also writes a CSV to the
 * app's files/results folder. Run with `task spike-android-vectors` or the phone kit command.
 */
@RunWith(AndroidJUnit4::class)
class VectorStorageSpikeTest {

    private val tag = "EYKO31"
    private val dim = 512
    private val queryCount = 20
    private val topK = 20

    private fun unitVectors(random: Random, count: Int): Array<FloatArray> = Array(count) {
        val v = FloatArray(dim) { random.nextGaussian().toFloat() }
        val norm = sqrt(v.fold(0.0) { acc, x -> acc + x * x }).toFloat()
        FloatArray(dim) { i -> v[i] / norm }
    }

    private fun toBlob(v: FloatArray): ByteArray =
        ByteBuffer.allocate(v.size * 4).order(ByteOrder.LITTLE_ENDIAN).apply { asFloatBuffer().put(v) }.array()

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

    private fun readMatrix(db: SQLiteDatabase, rows: Int): FloatArray {
        val matrix = FloatArray(rows * dim)
        db.rawQuery("SELECT embedding FROM image_vec ORDER BY frame_id", null).use { cursor ->
            var r = 0
            while (cursor.moveToNext()) {
                ByteBuffer.wrap(cursor.getBlob(0)).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(matrix, r * dim, dim)
                r++
            }
        }
        return matrix
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
     * it reads the whole table per query), commit (the kit's commit hash).
     */
    @Test
    fun blobColumnWithBruteForceSearch() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val args = InstrumentationRegistry.getArguments()
        val sizes = (args.getString("sizes") ?: "5k,20k").split(",").map { parseSize(it) }
        val runs = args.getString("runs")?.toInt() ?: 5
        val diskMax = parseSize(args.getString("diskMax") ?: "20k")
        val commit = args.getString("commit") ?: "unknown"

        val sqlite = SQLiteDatabase.create(null).use { db ->
            db.rawQuery("SELECT sqlite_version()", null).use { it.moveToFirst(); it.getString(0) }
        }
        val device = "${Build.MANUFACTURER} ${Build.MODEL}"
        val date = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(Date())
        val ram = ActivityManager.MemoryInfo().also { context.getSystemService(ActivityManager::class.java).getMemoryInfo(it) }
        Log.i(tag, "device sheet: $device, Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}), sqlite $sqlite, commit $commit, date $date")
        Log.i(
            tag,
            "device sheet: RAM %.1f GB, java heap limit %.0f MB, free storage %.1f GB, sizes %s, runs %d, diskMax %d".format(
                Locale.ROOT, ram.totalMem / 1e9, Runtime.getRuntime().maxMemory() / 1e6,
                context.filesDir.usableSpace / 1e9, sizes, runs, diskMax,
            ),
        )

        val outDir = context.getExternalFilesDir("results")!!.apply { mkdirs() }
        val csv = File(outDir, "eyko90-${Build.MODEL.replace(Regex("[^A-Za-z0-9]+"), "_")}-${SimpleDateFormat("yyyyMMdd-HHmm", Locale.ROOT).format(Date())}.csv")
        csv.writeText(CSV_HEADER + "\n")
        fun row(method: String, n: Int, run: String, times: List<Double>?, fileMb: Double, tempStart: Double?, note: String = "") {
            val runtime = Runtime.getRuntime()
            val battery = battery(context)
            val stats = times?.sorted()?.let { s ->
                listOf(s[s.size / 2], s[ceil(0.95 * s.size).toInt() - 1], s.last()).joinToString(",") { "%.2f".format(Locale.ROOT, it) }
            } ?: ",,"
            csv.appendText(
                listOf(
                    device, Build.VERSION.RELEASE, sqlite, commit, date, method, dim, n, run, stats,
                    "%.0f".format(Locale.ROOT, Debug.getPss() / 1024.0),
                    "%.0f".format(Locale.ROOT, (runtime.totalMemory() - runtime.freeMemory()) / 1e6),
                    "%.1f".format(Locale.ROOT, fileMb),
                    tempStart?.let { "%.1f".format(Locale.ROOT, it) } ?: "",
                    "%.1f".format(Locale.ROOT, battery.first), battery.second, "random_unit_seed31", note.replace(",", ";"),
                ).joinToString(",") + "\n",
            )
            if (times != null) report("n=$n $method run $run", times)
        }

        val queries = unitVectors(Random(90), queryCount + 1) // the first one is the warm-up
        for (n in sizes) {
            val file = context.getDatabasePath("eyko90_sweep_$n.db")
            file.parentFile?.mkdirs()
            file.delete()
            val db = SQLiteDatabase.openOrCreateDatabase(file, null)
            try {
                db.execSQL("CREATE TABLE image_vec (frame_id INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
                val random = Random(31)
                val insertMs = timeMs {
                    db.beginTransaction()
                    val insert = db.compileStatement("INSERT INTO image_vec VALUES (?, ?)")
                    for (i in 0 until n) {
                        insert.bindLong(1, i.toLong())
                        insert.bindBlob(2, toBlob(unitVectors(random, 1)[0]))
                        insert.executeInsert()
                    }
                    db.setTransactionSuccessful()
                    db.endTransaction()
                }
                val fileMb = file.length() / 1e6
                Log.i(tag, "n=$n insert all: %.0f ms, file %.1f MB".format(Locale.ROOT, insertMs, fileMb))

                if (n <= diskMax) {
                    try {
                        topK(readMatrix(db, n), n, queries[0])
                        for (run in 1..runs) {
                            val tempStart = battery(context).first
                            row("blob_disk_dot", n, "$run", queries.drop(1).map { q -> timeMs { topK(readMatrix(db, n), n, q) } }, fileMb, tempStart)
                        }
                    } catch (e: OutOfMemoryError) {
                        row("blob_disk_dot", n, "", null, fileMb, null, "OutOfMemoryError: ${e.message}")
                        Log.i(tag, "n=$n blob_disk_dot: OutOfMemoryError: ${e.message}")
                    }
                } else {
                    row("blob_disk_dot", n, "", null, fileMb, null, "skipped: over diskMax $diskMax")
                }

                try {
                    val matrix = readMatrix(db, n)
                    topK(matrix, n, queries[0])
                    for (run in 1..runs) {
                        val tempStart = battery(context).first
                        row("blob_memory_dot", n, "$run", queries.drop(1).map { q -> timeMs { topK(matrix, n, q) } }, fileMb, tempStart)
                    }
                } catch (e: OutOfMemoryError) {
                    row("blob_memory_dot", n, "", null, fileMb, null, "OutOfMemoryError: ${e.message}")
                    Log.i(tag, "n=$n blob_memory_dot: OutOfMemoryError: ${e.message}")
                }
            } finally {
                db.close()
                file.delete()
            }
        }
        Log.i(tag, "csv written: ${csv.absolutePath}")
        Log.i(tag, "pull it with: adb pull ${csv.absolutePath}")
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
