package com.eykon.memory.spike

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.os.Build
import android.os.Debug
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Random
import kotlin.math.sqrt

/**
 * EYKO-31 spike (throwaway): can the phone's SQLite use sqlite-vec, and how fast is the
 * plain alternative (float32 BLOB column + brute-force dot product)?
 * Results go to logcat under the tag EYKO31. Run with `task spike-android-vectors`.
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

    @Test
    fun blobColumnWithBruteForceSearch() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        for (rows in intArrayOf(5_000, 20_000)) {
            val random = Random(31)
            val vectors = unitVectors(random, rows)
            val queries = unitVectors(random, queryCount)
            val file = context.getDatabasePath("eyko31_spike_$rows.db")
            file.parentFile?.mkdirs()
            file.delete()
            val db = SQLiteDatabase.openOrCreateDatabase(file, null)
            try {
                db.execSQL("CREATE TABLE image_vec (frame_id INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
                val insertMs = timeMs {
                    db.beginTransaction()
                    val insert = db.compileStatement("INSERT INTO image_vec VALUES (?, ?)")
                    vectors.forEachIndexed { i, v ->
                        insert.bindLong(1, i.toLong())
                        insert.bindBlob(2, toBlob(v))
                        insert.executeInsert()
                    }
                    db.setTransactionSuccessful()
                    db.endTransaction()
                }
                Log.i(tag, "n=$rows insert all: %.0f ms, file %.1f MB".format(insertMs, file.length() / 1e6))

                report("n=$rows BLOB read from SQLite + dot", queries.map { q -> timeMs { topK(readMatrix(db, rows), rows, q) } })

                val matrix = readMatrix(db, rows)
                report("n=$rows BLOB already in memory, dot only", queries.map { q -> timeMs { topK(matrix, rows, q) } })

                val runtime = Runtime.getRuntime()
                Log.i(
                    tag,
                    "n=$rows memory: java heap used %.0f MB, native heap %.0f MB".format(
                        (runtime.totalMemory() - runtime.freeMemory()) / 1e6,
                        Debug.getNativeHeapAllocatedSize() / 1e6,
                    ),
                )
            } finally {
                db.close()
                file.delete()
            }
        }
    }
}
