package com.eykon.memory.video

import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min

/**
 * Difference hash (dHash) of a picture, card EYKO-6: shrink it to 9x8 gray values and write one
 * bit per value that is brighter than its left neighbour: 64 bits that stay almost the same when
 * the picture barely changes. Same result as OpenCV on the laptop (src/benchmarks/filters_golden.py).
 * Pure Kotlin, so it runs in JVM tests.
 */
object FrameHash {

    private const val COLUMNS = 9
    private const val ROWS = 8

    fun dHash(gray: Gray): Long {
        val tiny = shrink(gray, COLUMNS, ROWS)
        var hash = 0L
        for (y in 0 until ROWS) {
            for (x in 1 until COLUMNS) {
                hash = (hash shl 1) or (if (tiny[y * COLUMNS + x] > tiny[y * COLUMNS + x - 1]) 1L else 0L)
            }
        }
        return hash
    }

    /** How many of the 64 bits differ. */
    fun distance(a: Long, b: Long): Int = java.lang.Long.bitCount(a xor b)

    fun toHex(hash: Long): String = "%016x".format(hash)

    /**
     * Area averaging: each output value is the average of the part of the picture it covers,
     * with edge pixels counted by the fraction covered, rounded to a whole gray level.
     */
    private fun shrink(gray: Gray, outWidth: Int, outHeight: Int): IntArray {
        val scaleX = gray.width / outWidth.toDouble()
        val scaleY = gray.height / outHeight.toDouble()
        val out = IntArray(outWidth * outHeight)
        for (oy in 0 until outHeight) {
            val top = oy * scaleY
            val bottom = (oy + 1) * scaleY
            for (ox in 0 until outWidth) {
                val left = ox * scaleX
                val right = (ox + 1) * scaleX
                var sum = 0.0
                for (y in floor(top).toInt() until min(gray.height, ceil(bottom).toInt())) {
                    val weightY = min(bottom, y + 1.0) - max(top, y.toDouble())
                    for (x in floor(left).toInt() until min(gray.width, ceil(right).toInt())) {
                        val weightX = min(right, x + 1.0) - max(left, x.toDouble())
                        sum += gray.pixels[y * gray.width + x] * weightX * weightY
                    }
                }
                out[oy * outWidth + ox] = Math.rint(sum / (scaleX * scaleY)).toInt()
            }
        }
        return out
    }
}
