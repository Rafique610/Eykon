package com.eykon.memory.ml.vision

import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min

/**
 * Turns a picture into a model's square input: red, green and blue planes with values 0 to 1,
 * stretched by the plain two-by-two blend (PyTorch's bilinear without corner alignment), which is what
 * the laptop's D-FINE processor does.
 */
internal object ImagePrep {

    /**
     * [argb] is [width] x [height], stretched to [side] x [side].
     * [wholeValues] rounds each blended colour to a whole number first, as resizing 8-bit colours does.
     */
    fun rgbPlanes(argb: IntArray, width: Int, height: Int, side: Int, wholeValues: Boolean = false): FloatArray {
        val plane = side * side
        val out = FloatArray(3 * plane)
        val scaleX = width / side.toDouble()
        val scaleY = height / side.toDouble()
        fun colour(x: Int, y: Int, shift: Int): Float = ((argb[y * width + x] shr shift) and 0xFF).toFloat()
        for (y in 0 until side) {
            val fy = max(0.0, (y + 0.5) * scaleY - 0.5)
            val y0 = min(floor(fy).toInt(), height - 1)
            val y1 = min(y0 + 1, height - 1)
            val wy = (fy - y0).toFloat()
            for (x in 0 until side) {
                val fx = max(0.0, (x + 0.5) * scaleX - 0.5)
                val x0 = min(floor(fx).toInt(), width - 1)
                val x1 = min(x0 + 1, width - 1)
                val wx = (fx - x0).toFloat()
                for ((channel, shift) in listOf(16, 8, 0).withIndex()) { // red, green, blue
                    val top = colour(x0, y0, shift) * (1 - wx) + colour(x1, y0, shift) * wx
                    val bottom = colour(x0, y1, shift) * (1 - wx) + colour(x1, y1, shift) * wx
                    val value = top * (1 - wy) + bottom * wy
                    out[channel * plane + y * side + x] = (if (wholeValues) Math.round(value).toFloat() else value) / 255f
                }
            }
        }
        return out
    }
}
