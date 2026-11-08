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
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.Random
import kotlin.math.ceil
import kotlin.math.sqrt

/** Shared by the phone benchmarks (EYKO-90, EYKO-100, EYKO-102): vectors, the CSV sheet, battery. */
object TestVectors {

    fun unit(v: FloatArray): FloatArray {
        val norm = sqrt(v.fold(0.0) { acc, x -> acc + x * x }).toFloat()
        for (i in v.indices) v[i] /= norm
        return v
    }

    /**
     * Endless unit vectors of [size] numbers. "random": Gaussian, fixed seed. "real" (EYKO-100):
     * the vectors of our own clips in the test assets (90 per table), first as they are, then
     * repeated with small noise (0.01 per number, about 0.97 cosine to the original).
     */
    fun stream(source: String, size: Int, seed: Long): () -> FloatArray {
        val random = Random(seed)
        if (source != "real") return { unit(FloatArray(size) { random.nextGaussian().toFloat() }) }
        val base = real(size)
        var i = 0
        return {
            val b = base[i % base.size]
            i++
            if (i <= base.size) b.copyOf() else unit(FloatArray(size) { b[it] + 0.01f * random.nextGaussian().toFloat() })
        }
    }

    fun real(size: Int): List<FloatArray> {
        val name = if (size == 512) "vectors/own_image_512.f32" else "vectors/own_text_384.f32"
        val bytes = InstrumentationRegistry.getInstrumentation().context.assets.open(name).use { it.readBytes() }
        val floats = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
        return List(floats.remaining() / size) { FloatArray(size).also { v -> floats.get(v) } }
    }

    /** [count] queries. Random: the stream with seed 90 (EYKO-90's queries). Real: our own frames with more noise (0.05 per number). */
    fun queries(source: String, size: Int, count: Int): List<FloatArray> {
        if (source != "real") return stream(source, size, 90).let { next -> List(count) { next() } }
        val base = real(size)
        val random = Random(90)
        return List(count) { q -> unit(FloatArray(size) { base[(q * 7) % base.size][it] + 0.05f * random.nextGaussian().toFloat() }) }
    }

    fun label(source: String) = if (source == "real") "real_own_clips_90+noise" else "random_unit_seed31"

    fun toBlob(v: FloatArray): ByteArray =
        ByteBuffer.allocate(v.size * 4).order(ByteOrder.LITTLE_ENDIAN).apply { asFloatBuffer().put(v) }.array()
}

/**
 * EYKO-100's fast exact search (blob_memory_fast): four running sums per row and a [k]-slot
 * min-heap instead of sorting every row. Row indexes of the best [k], best first.
 */
fun exactTopK(matrix: FloatArray, rows: Int, dim: Int, query: FloatArray, k: Int): List<Int> {
    val ids = IntArray(k)
    val best = FloatArray(k)
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
        if (size < k) {
            var c = size++
            while (c > 0 && best[(c - 1) / 2] > score) { // sift up
                best[c] = best[(c - 1) / 2]; ids[c] = ids[(c - 1) / 2]; c = (c - 1) / 2
            }
            best[c] = score; ids[c] = r
        } else if (score > best[0]) {
            var c = 0
            while (true) { // sift down
                var child = 2 * c + 1
                if (child >= k) break
                if (child + 1 < k && best[child + 1] < best[child]) child++
                if (best[child] >= score) break
                best[c] = best[child]; ids[c] = ids[child]; c = child
            }
            best[c] = score; ids[c] = r
        }
    }
    return (0 until size).sortedByDescending { best[it] }.map { ids[it] }
}

/** Total PSS in MB after two GCs (EYKO-100 memory tests). */
fun pssMb(): Double {
    repeat(2) { Runtime.getRuntime().gc(); System.runFinalization() }
    Thread.sleep(300)
    return Debug.MemoryInfo().also { Debug.getMemoryInfo(it) }.totalPss / 1024.0
}

fun parseSize(text: String): Int = text.trim().lowercase(Locale.ROOT).let {
    if (it.endsWith("k")) it.dropLast(1).toInt() * 1_000 else it.toInt()
}

fun timeMs(block: () -> Unit): Double {
    val start = System.nanoTime()
    block()
    return (System.nanoTime() - start) / 1e6
}

/** (battery temperature in °C, battery level in %), from the sticky battery broadcast. */
fun battery(context: Context): Pair<Double, Int> {
    val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))!!
    val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) * 100 / intent.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
    return intent.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0) / 10.0 to level
}

/** Prints the device sheet and writes CSV rows in the shared laptop/phone format (EYKO-90) to files/results. */
class BenchSheet(
    private val context: Context, private val tag: String, prefix: String, private val commit: String, private val source: String,
    sqliteVersion: String? = null, // a bundled SQLite's version (EYKO-105); default: the platform's
) {
    private val sqlite = sqliteVersion ?: SQLiteDatabase.create(null).use { db ->
        db.rawQuery("SELECT sqlite_version()", null).use { it.moveToFirst(); it.getString(0) }
    }
    private val device = "${Build.MANUFACTURER} ${Build.MODEL}"
    private val date = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(Date())
    val stamp: String = SimpleDateFormat("yyyyMMdd-HHmm", Locale.ROOT).format(Date())
    val outDir: File = context.getExternalFilesDir("results")!!.apply { mkdirs() }
    private val csv = File(outDir, "$prefix-${Build.MODEL.replace(Regex("[^A-Za-z0-9]+"), "_")}-$stamp.csv")

    init {
        val ram = ActivityManager.MemoryInfo().also { context.getSystemService(ActivityManager::class.java).getMemoryInfo(it) }
        Log.i(tag, "device sheet: $device, Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}), sqlite $sqlite, commit $commit, date $date")
        Log.i(
            tag,
            "device sheet: RAM %.1f GB, java heap limit %.0f MB, free storage %.1f GB, vectors %s".format(
                Locale.ROOT, ram.totalMem / 1e9, Runtime.getRuntime().maxMemory() / 1e6, context.filesDir.usableSpace / 1e9, source,
            ),
        )
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
        if (times != null) {
            val sorted = times.sorted()
            Log.i(tag, "n=$n $method run $run: median %.2f ms, worst %.2f ms".format(Locale.ROOT, sorted[sorted.size / 2], sorted.last()))
        } else if (note.isNotEmpty()) {
            Log.i(tag, "n=$n $method: $note")
        }
    }

    fun done() {
        Log.i(tag, "csv written: ${csv.absolutePath}")
        Log.i(tag, "pull it with: adb pull ${csv.absolutePath}")
    }

    private companion object {
        /** The shared laptop/phone format from EYKO-90, plus a last `note` column for skips and failures. */
        const val CSV_HEADER = "device,android,sqlite_version,commit,date,method,dim,n,run,median_ms,p95_ms,worst_ms," +
            "pss_mb,heap_mb,file_mb,temp_c_start,temp_c_end,battery_pct,source_vectors,note"
    }
}
