package com.eykon.memory.video

import org.junit.Assert.assertEquals
import org.junit.Test

/** Card EYKO-58: the same window rule as src/benchmarks/ego4d_eval.py `windows` (grow 0.85, gap 10 s, +-1.5 s). */
class SearchWindowsTest {

    @Test
    fun neighboursThatStillMatchJoinTheHitAndAWeakerOneStopsIt() {
        val times = doubleArrayOf(0.0, 3.0, 6.0, 9.0, 30.0)
        val scores = floatArrayOf(0.5f, 0.9f, 0.8f, 0.7f, 0.85f)
        // floor 0.765: 0.8 joins on the right, 0.7 stops it; 0.5 stops it on the left
        assertEquals(1.5 to 7.5, SearchWindows.grow(times, scores, 1))
    }

    @Test
    fun aGapOfMoreThanTenSecondsIsNeverBridged() {
        assertEquals(18.5 to 21.5, SearchWindows.grow(doubleArrayOf(0.0, 20.0), floatArrayOf(0.9f, 0.9f), 1))
    }

    @Test
    fun aWindowNeverStartsBeforeTheVideo() {
        assertEquals(0.0 to 1.5, SearchWindows.grow(doubleArrayOf(0.0), floatArrayOf(0.3f), 0))
    }
}
