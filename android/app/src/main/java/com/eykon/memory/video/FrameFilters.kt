package com.eykon.memory.video

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.roundToInt
import kotlin.math.sqrt

/** A small gray picture: one value from 0 to 255 per pixel, row by row. */
class Gray(val width: Int, val height: Int, val pixels: IntArray)

/**
 * The cheap frame checks of card EYKO-5: plain maths, no neural network, cheapest first, and a
 * frame leaves at the first check it fails (the cascaded early-exit idea of NoScope, VLDB 2017).
 * Every measure gives the same number as OpenCV on the laptop; the test pictures and OpenCV's
 * values are in src/test/resources/filters (made by src/benchmarks/filters_golden.py).
 * Pure Kotlin, so it runs in JVM tests.
 */
object FrameFilters {

    const val SMALL_SIDE = 320 // the longer side after shrinking by a whole-number factor
    private const val BINS = 64

    /** Starting values from the card. Tune them on real clips; they are not yet tuned. */
    data class Thresholds(
        val darkMax: Double = 25.0,
        val brightMin: Double = 235.0,
        val blurMin: Double = 60.0,
        val diffMin: Double = 6.0,
        val histMin: Double = 0.10,
    )

    /** Colour pixels (0xAARRGGBB) to gray, shrunk so the longer side is about [SMALL_SIDE]. */
    fun smallGray(argb: IntArray, width: Int, height: Int): Gray {
        val k = max(1, (max(width, height) / SMALL_SIDE.toDouble()).roundToInt())
        val outWidth = width / k
        val outHeight = height / k
        val out = IntArray(outWidth * outHeight)
        val half = k * k / 2
        for (y in 0 until outHeight) {
            for (x in 0 until outWidth) {
                var sum = 0
                for (dy in 0 until k) {
                    val row = (y * k + dy) * width + x * k
                    for (dx in 0 until k) {
                        val p = argb[row + dx]
                        // OpenCV's integer weights for 0.299 R + 0.587 G + 0.114 B
                        sum += (((p shr 16) and 0xFF) * 9798 + ((p shr 8) and 0xFF) * 19235 + (p and 0xFF) * 3735 + 16384) shr 15
                    }
                }
                out[y * outWidth + x] = (sum + half) / (k * k)
            }
        }
        return Gray(outWidth, outHeight, out)
    }

    fun brightness(gray: Gray): Double = gray.pixels.sumOf { it.toLong() }.toDouble() / gray.pixels.size

    /**
     * Sharpness: the variance of the Laplacian (Pech-Pacheco et al., ICPR 2000). The Laplacian
     * is the 4-neighbour kernel [0 1 0; 1 -4 1; 0 1 0]; at the border the picture is mirrored.
     * A blurry picture has weak edges, so the values barely vary.
     */
    fun laplacianVariance(gray: Gray): Double {
        val w = gray.width
        val h = gray.height
        val p = gray.pixels
        var sum = 0.0
        var sumSquares = 0.0
        for (y in 0 until h) {
            val up = (if (y == 0) 1 else y - 1) * w
            val down = (if (y == h - 1) h - 2 else y + 1) * w
            val row = y * w
            for (x in 0 until w) {
                val left = if (x == 0) 1 else x - 1
                val right = if (x == w - 1) w - 2 else x + 1
                val value = (p[up + x] + p[down + x] + p[row + left] + p[row + right] - 4 * p[row + x]).toDouble()
                sum += value
                sumSquares += value * value
            }
        }
        val n = (w * h).toDouble()
        val mean = sum / n
        return sumSquares / n - mean * mean
    }

    /** How much two pictures differ, pixel by pixel, on average. */
    fun meanAbsDiff(a: Gray, b: Gray): Double {
        var sum = 0L
        for (i in a.pixels.indices) sum += abs(a.pixels[i] - b.pixels[i])
        return sum.toDouble() / a.pixels.size
    }

    /** How much the spread of gray levels changed (Bhattacharyya distance, 64 bins): 0 same, 1 nothing shared. */
    fun histChange(a: Gray, b: Gray): Double {
        val ha = histogram(a)
        val hb = histogram(b)
        var shared = 0.0
        for (i in 0 until BINS) shared += sqrt(ha[i].toDouble() * hb[i])
        return sqrt(max(0.0, 1.0 - shared / sqrt(ha.sum().toDouble() * hb.sum())))
    }

    private fun histogram(gray: Gray): LongArray {
        val bins = LongArray(BINS)
        for (value in gray.pixels) bins[value * BINS / 256]++
        return bins
    }

    /**
     * The reason to drop this frame, or null to keep it. [previousKept] is the last frame that
     * was kept. The checks run in this order and stop at the first one that fails.
     */
    fun check(previousKept: Gray?, gray: Gray, t: Thresholds = Thresholds()): String? {
        val brightness = brightness(gray)
        if (brightness < t.darkMax) return "dark"
        if (brightness > t.brightMin) return "bright"
        if (laplacianVariance(gray) < t.blurMin) return "blurry"
        if (previousKept != null && previousKept.width == gray.width && previousKept.height == gray.height &&
            meanAbsDiff(previousKept, gray) < t.diffMin && histChange(previousKept, gray) < t.histMin
        ) return "still"
        return null
    }
}
