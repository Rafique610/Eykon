package com.eykon.memory.video

import android.content.Context
import android.os.Build
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel
import java.util.Locale
import kotlin.math.abs
import kotlin.math.roundToInt

/**
 * Hypotheses 2 + 3 (decision re-check, 26 Nov), phone part: the laptop showed that an int8 pass plus exact float32 scores for
 * the best candidates and their neighbours returns exactly the app's windows (52 of 52 queries, certified), reading 52 MB
 * instead of 205 MB at 100k. Is the int8 pass faster than today's float32 pass on a phone? Both from memory-mapped files of
 * the same 100k x 512 rows, scored in place by NEON (scoreF32 = MAPPED_NATIVE, scoreI8 = the new quick pass); median of
 * 11 searches after 2 warm-ups. Also checks the int8 scores stay within their error bound. Own files in the cache folder,
 * deleted at the end. Logcat tag EYKO_I8. Argument `-e n 100000`.
 */
@RunWith(AndroidJUnit4::class)
class Int8PassTest {

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val dim = 512
    private val chunkRows = 32768

    private fun vector(seed: Long, out: FloatArray) {
        var x = seed * 6364136223846793005L + 1442695040888963407L
        var norm = 0.0
        for (i in 0 until dim) {
            x = x * 6364136223846793005L + 1442695040888963407L
            out[i] = ((x ushr 40).toInt() / 16777216f) - 0.5f
            norm += out[i] * out[i]
        }
        val n = kotlin.math.sqrt(norm).toFloat()
        for (i in 0 until dim) out[i] /= n
    }

    private fun map(file: File, rowBytes: Int, rows: Int): List<ByteBuffer> = RandomAccessFile(file, "r").use { f ->
        (0 until (rows + chunkRows - 1) / chunkRows).map { c ->
            val n = minOf(chunkRows, rows - c * chunkRows)
            f.channel.map(FileChannel.MapMode.READ_ONLY, c.toLong() * chunkRows * rowBytes, n.toLong() * rowBytes).order(ByteOrder.LITTLE_ENDIAN)
        }
    }

    @Test
    fun int8PassAgainstFloat32Pass() {
        val n = InstrumentationRegistry.getArguments().getString("n")?.toInt() ?: 100_000
        val f32 = File(context.cacheDir, "eyko_i8_test.f32")
        val i8 = File(context.cacheDir, "eyko_i8_test.i8")
        val scales = FloatArray(n)
        try {
            val v = FloatArray(dim)
            f32.outputStream().buffered(1 shl 20).use { a ->
                i8.outputStream().buffered(1 shl 20).use { b ->
                    val fb = ByteBuffer.allocate(dim * 4).order(ByteOrder.LITTLE_ENDIAN)
                    val ib = ByteArray(dim)
                    for (r in 0 until n) {
                        vector(r.toLong(), v)
                        fb.clear(); v.forEach { fb.putFloat(it) }; a.write(fb.array())
                        val s = v.maxOf { abs(it) } / 127f
                        scales[r] = s
                        for (i in 0 until dim) ib[i] = (v[i] / s).roundToInt().coerceIn(-127, 127).toByte()
                        b.write(ib)
                    }
                }
            }
            val fChunks = map(f32, dim * 4, n)
            val iChunks = map(i8, dim, n)
            val q = FloatArray(dim).also { vector(7_000_001L, it) }
            val qs = q.maxOf { abs(it) } / 127f
            val qc = ByteArray(dim) { (q[it] / qs).roundToInt().coerceIn(-127, 127).toByte() }
            val exact = FloatArray(n)
            val approx = FloatArray(n)
            fun passF32() = fChunks.forEachIndexed { c, b -> VectorNative.scoreF32(b, minOf(chunkRows, n - c * chunkRows), dim, q, exact, c * chunkRows) }
            fun passI8() = iChunks.forEachIndexed { c, b ->
                val rows = minOf(chunkRows, n - c * chunkRows)
                VectorNative.scoreI8(b, rows, dim, scales.copyOfRange(c * chunkRows, c * chunkRows + rows), qc, qs, approx, c * chunkRows)
            }
            fun time(pass: () -> Unit): Double { repeat(2) { pass() }; return DoubleArray(11) { val t = System.nanoTime(); pass(); (System.nanoTime() - t) / 1e6 }.sorted()[5] }
            val msF32 = time(::passF32)
            val msI8 = time(::passI8)
            // the bound the laptop used: |v.q - approx| <= (s/2)|q|_1 + s |c|_1 (qs/2)
            val q1 = q.sumOf { abs(it).toDouble() }
            var worst = 0.0
            var outside = 0
            for (r in 0 until n) {
                val err = abs(exact[r] - approx[r]).toDouble()
                val bound = scales[r] / 2 * q1 + scales[r] * 127.0 * dim * (qs / 2) // |c|_1 <= 127 * dim: a looser, safe bound
                worst = maxOf(worst, err)
                if (err > bound) outside++
            }
            val line = "device %s %s, Android %s, %d rows x %d: float32 pass %.1f ms, int8 pass %.1f ms (%.2fx), largest int8 error %.5f, rows outside the bound %d"
                .format(Locale.ROOT, Build.MANUFACTURER, Build.MODEL, Build.VERSION.RELEASE, n, dim, msF32, msI8, msF32 / msI8, worst, outside)
            Log.i("EYKO_I8", line)
            assertTrue("int8 scores outside their error bound", outside == 0)
        } finally {
            f32.delete(); i8.delete()
        }
    }
}
