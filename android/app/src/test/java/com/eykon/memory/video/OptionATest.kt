package com.eykon.memory.video

import com.eykon.memory.ml.vision.Detection
import com.eykon.memory.ml.vision.ObjectDetector
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import kotlin.math.ln

/** The plain maths of perception Option A. The models themselves are tested on a phone (OptionAPhoneTest). */
class OptionATest {

    private val side = ObjectDetector.SIDE

    // ── Step 1: fit the picture into the model's square ─────────────────────────

    @Test
    fun aWidePictureIsShrunkToFitAndTheRestIsGrey() {
        val red = 0xFFFF0000.toInt()
        val (input, ratio) = ObjectDetector.letterbox(IntArray(832 * 416) { red }, 832, 416)

        assertEquals(0.5f, ratio, 1e-6f)
        val plane = side * side
        val inside = 100 * side + 200 // row 100 is within the 208 rows the picture fills
        val below = 300 * side + 200
        // blue plane, green plane, red plane
        assertEquals(listOf(0f, 0f, 255f), listOf(input[inside], input[plane + inside], input[2 * plane + inside]))
        assertEquals(listOf(114f, 114f, 114f), listOf(input[below], input[plane + below], input[2 * plane + below]))
    }

    @Test
    fun shrinkingBlendsNeighbouringPixels() {
        // 832 wide, columns alternate black and white: halving it must give mid grey everywhere
        val pixels = IntArray(832 * 416) { if (it % 2 == 0) 0xFF000000.toInt() else 0xFFFFFFFF.toInt() }
        val (input, _) = ObjectDetector.letterbox(pixels, 832, 416)
        assertEquals(128f, input[50 * side + 50], 0.5f)
    }

    // ── Step 2: model rows to boxes ─────────────────────────────────────────────

    private fun silentRows() = Array(52 * 52 + 26 * 26 + 13 * 13) { FloatArray(85) }

    @Test
    fun aRowBecomesABoxInThePicturesOwnPixels() {
        val rows = silentRows()
        // first grid (cells of 8 px), cell x = 3, y = 2; centre in the middle of the cell, 4 cells wide, 2 tall
        rows[2 * 52 + 3] = FloatArray(85).also {
            it[0] = 0.5f; it[1] = 0.5f; it[2] = ln(4f); it[3] = ln(2f)
            it[4] = 0.9f // something is there
            it[5 + 63] = 0.8f // laptop
        }
        val found = ObjectDetector.decode(rows, ratio = 0.5f, minConf = 0.35f)

        assertEquals(1, found.size)
        assertEquals("laptop", found[0].label)
        assertEquals(0.72f, found[0].conf, 1e-5f)
        // centre (28, 20), size 32 x 16 in the model's square; the picture is twice that size
        listOf(24f, 24f, 88f, 56f).forEachIndexed { i, expected -> assertEquals(expected, found[0].box[i], 1e-3f) }
    }

    @Test
    fun rowsFromTheCoarserGridsUseTheirOwnCellSize() {
        val rows = silentRows()
        rows[52 * 52 + 26 * 26 + 1] = FloatArray(85).also { it[4] = 1f; it[5] = 1f } // third grid (32 px), cell x = 1, y = 0
        val box = ObjectDetector.decode(rows, ratio = 1f, minConf = 0.35f).single().box
        assertEquals(listOf(16f, -16f, 48f, 16f), box) // centre (32, 0), size 32 x 32
    }

    @Test
    fun unsureRowsAreLeftOut() {
        val rows = silentRows()
        rows[0] = FloatArray(85).also { it[4] = 0.5f; it[5] = 0.6f } // 0.30 < 0.35
        assertEquals(emptyList<Detection>(), ObjectDetector.decode(rows, 1f, 0.35f))
    }

    // ── Step 3: the same thing seen twice is kept once ──────────────────────────

    @Test
    fun overlappingBoxesKeepOnlyTheSurestAndFarApartBoxesBothStay() {
        val sure = Detection("cup", 0.9f, listOf(10f, 10f, 110f, 110f))
        val same = Detection("bowl", 0.6f, listOf(15f, 15f, 115f, 115f))
        val elsewhere = Detection("cup", 0.5f, listOf(300f, 300f, 400f, 400f))

        assertEquals(listOf(sure, elsewhere), ObjectDetector.nms(listOf(elsewhere, same, sure)))
    }

    // ── People, place and action ────────────────────────────────────────────────

    @Test
    fun peopleAreCountedAndNotListedAsObjects() {
        val box = listOf(0f, 0f, 1f, 1f)
        val seen = OptionA.perception(listOf(Detection("person", 0.9f, box), Detection("laptop", 0.8f, box), Detection("person", 0.5f, box)), "an office", null)

        assertEquals(2, seen.people)
        assertEquals(listOf("laptop"), seen.objects.map { it.label })
        assertEquals("an office", seen.place)
        assertNull(seen.action)
        assertNull(seen.caption)
    }

    private val prompts = OptionA.Prompts(listOf("a kitchen", "a street", "an office"), listOf(floatArrayOf(1f, 0f, 0f), floatArrayOf(0f, 1f, 0f), floatArrayOf(0f, 0f, 1f)))

    @Test
    fun theBestFittingPhraseWins() {
        val nearStreet = floatArrayOf(0.1f, 0.99f, 0.1f)
        assertEquals("a street", OptionA.bestPrompt(nearStreet, prompts, 0.30f))
        assertEquals(1f, OptionA.probabilities(nearStreet, prompts.vectors).sum(), 1e-5f)
    }

    @Test
    fun aPictureThatFitsNoPhraseWellGetsNone() {
        val nothingInParticular = floatArrayOf(0.5f, 0.5f, 0.5f) // each phrase gets one third
        assertEquals("a kitchen", OptionA.bestPrompt(nothingInParticular, prompts, 0.30f))
        assertNull(OptionA.bestPrompt(nothingInParticular, prompts, 0.40f))
    }
}
