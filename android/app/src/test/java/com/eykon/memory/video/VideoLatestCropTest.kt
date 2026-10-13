package com.eykon.memory.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Which square part of the picture stands for an object's box. */
class VideoLatestCropTest {

    @Test
    fun aBoxInTheMiddleGetsASquareAsWideAsItsLongerSideAroundItsCentre() {
        // box 100 wide, 60 high, centred on (250, 130)
        assertEquals(Triple(200, 80, 100), VideoLatest.cropSquare(listOf(200f, 100f, 300f, 160f), 640, 360))
    }

    @Test
    fun aSquareThatWouldLeaveThePictureIsMovedInside() {
        // tall box at the left edge: the 200-pixel square cannot start left of 0
        assertEquals(Triple(0, 100, 200), VideoLatest.cropSquare(listOf(10f, 100f, 60f, 300f), 640, 360))
        // box at the right edge, 80 wide and 100 high: the 100-pixel square cannot end right of 640
        assertEquals(Triple(540, 250, 100), VideoLatest.cropSquare(listOf(560f, 250f, 640f, 350f), 640, 360))
    }

    @Test
    fun aBoxBiggerThanThePictureIsCutToItAndTheSquareIsNoBiggerThanTheShorterSide() {
        assertEquals(Triple(140, 0, 360), VideoLatest.cropSquare(listOf(-5f, -20f, 700f, 400f), 640, 360))
    }

    @Test
    fun aBoxTooSmallToJudgeGivesNothing() {
        assertNull(VideoLatest.cropSquare(listOf(100f, 100f, 110f, 200f), 640, 360)) // 10 wide
        assertNull(VideoLatest.cropSquare(listOf(630f, 100f, 700f, 200f), 640, 360)) // only 10 of it is inside the picture
    }

    @Test
    fun vectorsOfLengthOneCompareByTheirDotProduct() {
        assertEquals(0.6f, VideoLatest.cosine(floatArrayOf(1f, 0f), floatArrayOf(0.6f, 0.8f)), 1e-6f)
    }
}
