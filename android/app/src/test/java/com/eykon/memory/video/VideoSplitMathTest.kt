package com.eykon.memory.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin
import kotlin.math.sqrt

class VideoSplitMathTest {

    private fun resample(input: ShortArray, inRate: Int, channels: Int, chunk: Int = 1000): ShortArray {
        val out = ArrayList<Short>()
        val resampler = MonoResampler(inRate, channels)
        var position = 0
        while (position < input.size) { // fed in pieces, as the decoder delivers it
            val length = minOf(chunk, input.size - position)
            resampler.feed(input.copyOfRange(position, position + length), length) { out.add(it) }
            position += length
        }
        return out.toShortArray()
    }

    private fun tone(hz: Double, rate: Int, seconds: Double, channels: Int): ShortArray {
        val frames = (rate * seconds).toInt()
        return ShortArray(frames * channels) { i -> (8000 * sin(2 * PI * hz * (i / channels) / rate)).toInt().toShort() }
    }

    private fun rms(x: ShortArray) = sqrt(x.sumOf { it.toDouble() * it } / x.size)

    /** Upward zero crossings per second: the tone's frequency if the output rate is right. */
    private fun frequency(x: ShortArray, rate: Int): Double =
        (1 until x.size).count { x[it - 1] < 0 && x[it] >= 0 } / (x.size / rate.toDouble())

    @Test
    fun tenSecondsAtThreeFpsIsThirtyFrames() {
        val times = VideoSplit.frameTimes(10.0, 3.0)
        assertEquals(30, times.size)
        assertEquals(0.0, times.first(), 1e-9)
        assertEquals(9.667, times.last(), 0.001)
    }

    @Test
    fun aShortClipAndAnEmptyOne() {
        assertEquals(9, VideoSplit.frameTimes(2.912, 3.0).size)
        assertEquals(31, VideoSplit.frameTimes(10.01, 3.0).size)
        assertTrue(VideoSplit.frameTimes(0.0, 3.0).isEmpty())
    }

    @Test
    fun stereo48kBecomesMono16kOfTheSameLengthAndPitch() {
        val out = resample(tone(440.0, 48_000, 2.0, channels = 2), 48_000, 2)
        assertEquals(32_000, out.size)
        assertEquals(440.0, frequency(out, 16_000), 5.0)
        assertTrue(abs(rms(out) - 8000 / sqrt(2.0)) < 300)
    }

    @Test
    fun mono44100BecomesMono16k() {
        val out = resample(tone(440.0, 44_100, 2.0, channels = 1), 44_100, 1, chunk = 777)
        assertTrue(abs(out.size - 32_000) <= 1)
        assertEquals(440.0, frequency(out, 16_000), 5.0)
    }

    @Test
    fun sixteenKStaysAsItIsAndEightKIsDoubled() {
        val same = tone(440.0, 16_000, 1.0, channels = 1)
        assertTrue(same.contentEquals(resample(same, 16_000, 1)))
        assertEquals(16_000, resample(tone(440.0, 8_000, 1.0, channels = 1), 8_000, 1).size)
    }
}
