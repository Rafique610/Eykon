package com.eykon.memory.video

import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Random

class FrameFiltersTest {

    // ── The same numbers as OpenCV on the laptop ────────────────────────────────

    private val golden = TestPictures.golden

    private fun picture(name: String) = TestPictures.picture(name)

    @Test
    fun everyPictureMeasuresTheSameAsOpenCv() {
        for ((name, expected) in golden["pictures"]!!.jsonObject) {
            val want = expected.jsonObject
            val gray = picture(name)
            assertEquals("$name width", want["width"]!!.jsonPrimitive.int, gray.width)
            assertEquals("$name height", want["height"]!!.jsonPrimitive.int, gray.height)
            // The sum of all gray values is equal only if every step (colour to gray, shrinking) matches.
            assertEquals("$name gray values", want["checksum"]!!.jsonPrimitive.long, gray.pixels.sumOf { it.toLong() })
            assertEquals("$name brightness", want["brightness"]!!.jsonPrimitive.double, FrameFilters.brightness(gray), 1e-9)
            assertEquals("$name sharpness", want["laplacian_variance"]!!.jsonPrimitive.double, FrameFilters.laplacianVariance(gray), 1e-6)
        }
    }

    @Test
    fun everyPairDiffersTheSameAsOpenCv() {
        for ((name, expected) in golden["pairs"]!!.jsonObject) {
            val (first, second) = name.split("_vs_").map(::picture)
            val want = expected.jsonObject
            assertEquals("$name diff", want["diff"]!!.jsonPrimitive.double, FrameFilters.meanAbsDiff(first, second), 1e-9)
            assertEquals("$name histogram change", want["hist_change"]!!.jsonPrimitive.double, FrameFilters.histChange(first, second), 1e-6)
        }
    }

    @Test
    fun theBlurredPictureIsFarLessSharpThanTheSharpOne() {
        val sharp = FrameFilters.laplacianVariance(picture("sharp"))
        val blurred = FrameFilters.laplacianVariance(picture("blurred"))
        assertEquals("blurry", FrameFilters.check(null, picture("blurred")))
        assertNull(FrameFilters.check(null, picture("sharp")))
        assertTrue("sharp $sharp, blurred $blurred", sharp > 100 * blurred)
    }

    // ── The card's cases, with pictures made here ───────────────────────────────

    private fun flat(value: Int) = Gray(320, 180, IntArray(320 * 180) { value })

    private fun noise(seed: Long, low: Int = 0, high: Int = 256): Gray {
        val random = Random(seed)
        return Gray(320, 180, IntArray(320 * 180) { low + random.nextInt(high - low) })
    }

    @Test
    fun anAllBlackFrameIsDark() = assertEquals("dark", FrameFilters.check(null, flat(0)))

    @Test
    fun anAllWhiteFrameIsBright() = assertEquals("bright", FrameFilters.check(null, flat(255)))

    @Test
    fun aFrameWithNoDetailIsBlurry() = assertEquals("blurry", FrameFilters.check(null, flat(128)))

    @Test
    fun theSameFrameTwiceIsStillTheSecondTime() {
        val frame = noise(1)
        assertNull(FrameFilters.check(null, frame)) // the first good frame is always kept
        assertEquals("still", FrameFilters.check(frame, frame))
    }

    @Test
    fun twoVeryDifferentFramesAreBothKept() {
        val first = noise(1, 0, 120)
        val second = noise(2, 130, 256)
        assertNull(FrameFilters.check(null, first))
        assertNull(FrameFilters.check(first, second))
    }

    @Test
    fun aSmallChangeInBrightnessAloneIsNotEnoughToKeepAFrame() {
        val frame = noise(1, 40, 200)
        val slightlyBrighter = Gray(frame.width, frame.height, IntArray(frame.pixels.size) { frame.pixels[it] + 2 })
        assertEquals("still", FrameFilters.check(frame, slightlyBrighter))
    }

    @Test
    fun theChecksStopAtTheFirstOneThatFails() {
        // black and identical to the last kept frame: reported as dark, the earlier check
        assertEquals("dark", FrameFilters.check(flat(0), flat(0)))
    }

    @Test
    fun aFrameOfAnotherSizeIsNeverCalledStill() {
        val wide = noise(1)
        val tall = Gray(180, 320, wide.pixels.copyOf())
        assertNull(FrameFilters.check(wide, tall))
    }
}
