package com.eykon.memory.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Cards EYKO-60 (action smoothing) and EYKO-63 (which frames YOLOE looks at). */
class OptionASmoothTest {

    private fun unit(vararg v: Float) = v.let { a -> val n = kotlin.math.sqrt(a.sumOf { (it * it).toDouble() }).toFloat(); FloatArray(a.size) { a[it] / n } }
    private val actions = OptionA.Prompts(listOf("reading", "eating"), listOf(unit(1f, 0f), unit(0f, 1f)))

    @Test
    fun aLoneOddFrameTakesTheActionOfItsNeighbours() {
        val times = listOf(0.0, 3.0, 6.0, 30.0)
        val vectors = listOf(unit(1f, 0f), unit(0f, 1f), unit(1f, 0f), unit(0f, 1f))
        val out = OptionA.smoothActions(times, vectors, actions, listOf(null, null, null, null))
        // frame 2 (eating) sits between two reading frames within 6 s; frame 4 is alone, 24 s away
        assertEquals(listOf("reading", "reading", "reading", "eating"), out)
    }

    @Test
    fun aFrameWithoutAVectorKeepsItsOwnAction() {
        val out = OptionA.smoothActions(listOf(0.0, 3.0), listOf(unit(1f, 0f), null), actions, listOf(null, "eating"))
        assertEquals(listOf("reading", "eating"), out)
    }

    @Test
    fun anEvenSplitBelowTheFloorGivesNoAction() {
        // four frames close together, one per action: every averaged share is 0.25, below 0.30
        val axes = (0 until 4).map { a -> FloatArray(4) { if (it == a) 1f else 0f } }
        val four = OptionA.Prompts(listOf("a", "b", "c", "d"), axes)
        val out = OptionA.smoothActions(listOf(0.0, 1.0, 2.0, 3.0), axes, four, listOf(null, null, null, null))
        assertEquals(listOf<String?>(null, null, null, null), out)
    }

    @Test
    fun yoloeLooksOnlyAtFlaggedFramesOrFramesWithoutAVector() {
        val keys = unit(1f, 0f, 0f)
        assertTrue(OptionA.flagged(unit(1f, 1f, 0f), listOf(keys))) // cosine 0.71
        assertFalse(OptionA.flagged(unit(0.1f, 0f, 1f), listOf(keys))) // cosine 0.0995 < 0.15
        assertTrue(OptionA.flagged(null, listOf(keys)))
    }
}
