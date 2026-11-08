package com.eykon.memory.video

import android.util.Half
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.ShortBuffer
import java.nio.channels.FileChannel
import kotlin.math.roundToInt

/**
 * How [VideoVectors] holds a table in memory (EYKO-109). The database always stays float32 BLOBs.
 * HEAP_F32 is the app's way: one Java FloatArray. The others keep the numbers in direct or
 * memory-mapped buffers in chunks, so no single 600 MB allocation is needed.
 */
internal enum class VectorMode(val mapped: Boolean = false) {
    HEAP_F32, DIRECT_F32, DIRECT_F16, DIRECT_I8, MAPPED_F32(true),

    /** EYKO-114 option 1: the mapped file copied [BLOCK_ROWS] rows at a time, then the same dot() as the heap. */
    MAPPED_BLOCK(true),

    /** EYKO-114 option 2: scored in place in the mapped memory by NEON C code (libeykonvec.so), same sum order. */
    MAPPED_NATIVE(true),
}

/**
 * One table's vectors in chunked [ByteBuffer]s (every mode except HEAP_F32). With [readOnly] the
 * [mapFile] already holds every row (EYKO-115: written once, appended to) and is only mapped, not filled.
 */
internal class VectorBlock(private val mode: VectorMode, private val rows: Int, private val size: Int, mapFile: File?, readOnly: Boolean = false) {

    private val numberBytes = when (mode) { VectorMode.DIRECT_F16 -> 2; VectorMode.DIRECT_I8 -> 1; else -> 4 }
    private val rowBytes = size * numberBytes
    private val chunks: Array<ByteBuffer>
    private val floats: Array<FloatBuffer>?
    private val shorts: Array<ShortBuffer>?

    /** Bytes this block holds outside the Java FloatArray path. */
    val bytes: Long = rows.toLong() * rowBytes

    init {
        val file = mapFile?.let { RandomAccessFile(it, if (readOnly) "r" else "rw") }
        val mapMode = if (readOnly) FileChannel.MapMode.READ_ONLY else FileChannel.MapMode.READ_WRITE
        chunks = Array((rows + CHUNK_ROWS - 1) / CHUNK_ROWS) { c ->
            val length = minOf(CHUNK_ROWS, rows - c * CHUNK_ROWS) * rowBytes
            val buffer = if (file != null) {
                file.channel.map(mapMode, c.toLong() * CHUNK_ROWS * rowBytes, length.toLong())
            } else {
                ByteBuffer.allocateDirect(length)
            }
            buffer.order(ByteOrder.LITTLE_ENDIAN)
        }
        file?.close() // the mappings stay valid
        floats = if (numberBytes == 4) Array(chunks.size) { chunks[it].asFloatBuffer() } else null
        shorts = if (numberBytes == 2) Array(chunks.size) { chunks[it].asShortBuffer() } else null
    }

    /** Store row [row] from its float32 little-endian [blob], as the database holds it. */
    fun put(row: Int, blob: ByteArray) {
        val c = row / CHUNK_ROWS
        val local = row % CHUNK_ROWS
        when (mode) {
            VectorMode.DIRECT_F16 -> {
                val source = ByteBuffer.wrap(blob).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
                val target = shorts!![c]
                for (i in 0 until size) target.put(local * size + i, Half.toHalf(source.get(i)))
            }
            VectorMode.DIRECT_I8 -> {
                val source = ByteBuffer.wrap(blob).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
                val target = chunks[c]
                for (i in 0 until size) target.put(local * size + i, (source.get(i) * 127f).roundToInt().coerceIn(-127, 127).toByte())
            }
            else -> {
                val target = chunks[c]
                target.position(local * rowBytes)
                target.put(blob, 0, rowBytes)
            }
        }
    }

    /** Every row's likeness to [query] into [out]. float32 modes give the same numbers as the heap path. */
    fun scoreAll(query: FloatArray, out: FloatArray) {
        when (mode) {
            VectorMode.DIRECT_I8 -> scoreInt8(query, out)
            VectorMode.DIRECT_F16 -> {
                val half = ShortArray(size)
                val scratch = FloatArray(size)
                for (row in 0 until rows) {
                    val buffer = shorts!![row / CHUNK_ROWS]
                    buffer.position((row % CHUNK_ROWS) * size)
                    buffer.get(half, 0, size)
                    for (i in 0 until size) scratch[i] = Half.toFloat(half[i])
                    out[row] = VideoVectors.dot(scratch, 0, query)
                }
            }
            VectorMode.MAPPED_BLOCK -> {
                val scratch = FloatArray(BLOCK_ROWS * size)
                for (c in chunks.indices) {
                    val buffer = floats!![c]
                    val chunkRows = minOf(CHUNK_ROWS, rows - c * CHUNK_ROWS)
                    var start = 0
                    while (start < chunkRows) {
                        val n = minOf(BLOCK_ROWS, chunkRows - start)
                        buffer.position(start * size)
                        buffer.get(scratch, 0, n * size)
                        for (k in 0 until n) out[c * CHUNK_ROWS + start + k] = VideoVectors.dot(scratch, k * size, query)
                        start += n
                    }
                }
            }
            VectorMode.MAPPED_NATIVE -> for (c in chunks.indices) {
                VectorNative.scoreF32(chunks[c], minOf(CHUNK_ROWS, rows - c * CHUNK_ROWS), size, query, out, c * CHUNK_ROWS)
            }
            else -> {
                val scratch = FloatArray(size)
                for (row in 0 until rows) {
                    val buffer = floats!![row / CHUNK_ROWS]
                    buffer.position((row % CHUNK_ROWS) * size)
                    buffer.get(scratch, 0, size)
                    out[row] = VideoVectors.dot(scratch, 0, query)
                }
            }
        }
    }

    private fun scoreInt8(query: FloatArray, out: FloatArray) {
        val q = IntArray(size) { (query[it] * 127f).roundToInt().coerceIn(-127, 127) }
        val scratch = ByteArray(size)
        val scale = 1f / (127f * 127f)
        for (row in 0 until rows) {
            val buffer = chunks[row / CHUNK_ROWS]
            buffer.position((row % CHUNK_ROWS) * size)
            buffer.get(scratch, 0, size)
            var sum = 0
            for (i in 0 until size) sum += scratch[i] * q[i]
            out[row] = sum * scale
        }
    }

    private companion object {
        /** 32,768 rows: 64 MB of float32 at 512 numbers, 16 MB of int8. */
        const val CHUNK_ROWS = 32768

        /** MAPPED_BLOCK: rows copied per call, 2 MB of float32 at 512 numbers (EYKO-114). */
        const val BLOCK_ROWS = 1024
    }
}

/** EYKO-114 option 2: NEON scoring straight from a mapped (direct) buffer, libeykonvec.so (cpp/eykonvec.c). */
internal object VectorNative {
    init { System.loadLibrary("eykonvec") }

    /** Writes the dot product of [query] with each of the [rows] vectors in [buffer] to out[outOffset + row]. */
    @JvmStatic external fun scoreF32(buffer: java.nio.ByteBuffer, rows: Int, size: Int, query: FloatArray, out: FloatArray, outOffset: Int)
}
