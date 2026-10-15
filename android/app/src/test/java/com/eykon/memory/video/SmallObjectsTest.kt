package com.eykon.memory.video

import com.eykon.memory.ml.vision.Detection
import com.eykon.memory.ml.vision.DfineDetector
import com.eykon.memory.ml.vision.ImagePrep
import com.eykon.memory.ml.vision.YoloeDetector
import org.junit.Assert.assertEquals
import org.junit.Test

/** The plain maths of D-FINE, YOLOE and the "small_objects" stage (card EYKO-32). The models run in DetectorGoldenTest on a phone. */
class SmallObjectsTest {

    private fun thing(label: String, conf: Float, box: List<Float> = listOf(0f, 0f, 10f, 10f), source: String = "detector") = Detection(label, conf, box, source)

    @Test
    fun stretchingKeepsColoursAsZeroToOne() {
        val red = 0xFFFF0000.toInt()
        val planes = ImagePrep.rgbPlanes(IntArray(8 * 4) { red }, 8, 4, 4)
        assertEquals(listOf(1f, 0f, 0f), listOf(planes[5], planes[16 + 5], planes[32 + 5]))
    }

    @Test
    fun yoloeCentresTheFrameOnGrey() {
        val fit = YoloeDetector.fit(640, 360, 1f)
        assertEquals(listOf(0, 140), listOf(fit.left, fit.top)) // Ultralytics' letterbox for our 640 x 360 frames
        val planes = YoloeDetector.letterbox(IntArray(640 * 360) { 0xFFFF0000.toInt() }, 640, 360, fit)
        val plane = 640 * 640
        assertEquals(114f / 255f, planes[10 * 640 + 5], 1e-6f) // row 10 is grey padding
        assertEquals(listOf(1f, 0f, 0f), listOf(planes[200 * 640 + 5], planes[plane + 200 * 640 + 5], planes[2 * plane + 200 * 640 + 5]))
    }

    @Test
    fun objects365NamesBecomePlainWords() {
        assertEquals(listOf("wallet", "pen", "cell phone", "earphone", "keys"), listOf("Wallet/Purse", "Pen/Pencil", "Cell Phone", "earphone", "Key").map(DfineDetector::plain))
    }

    @Test
    fun dfineKeepsOnlySureQueriesInPixels() {
        val logits = arrayOf(floatArrayOf(-5f, 3f), floatArrayOf(-5f, -4f)) // query 0 sure of class 1, query 1 unsure
        val boxes = arrayOf(floatArrayOf(0.5f, 0.5f, 0.5f, 0.5f), floatArrayOf(0.1f, 0.1f, 0.1f, 0.1f))
        val found = DfineDetector.decode(logits, boxes, listOf("Person", "Wallet/Purse"), 640, 360, 0.5f)
        assertEquals(1, found.size)
        assertEquals("wallet", found[0].label)
        assertEquals(listOf(160f, 90f, 480f, 270f), found[0].box)
    }

    @Test
    fun yoloeGivesTheWordsTheAppTakesWithBoxesInTheFrame() {
        // two candidate boxes; words: keys, wallet, earbuds; the app takes keys and earbuds only
        val rows = arrayOf(
            floatArrayOf(300f, 100f), floatArrayOf(330f, 100f), floatArrayOf(40f, 10f), floatArrayOf(20f, 10f), // cx, cy, w, h
            floatArrayOf(0.2f, 0.7f), floatArrayOf(0.9f, 0.1f), floatArrayOf(0.1f, 0.2f), // keys, wallet, earbuds
        )
        val found = YoloeDetector.decode(rows, listOf("keys", "wallet", "earbuds"), setOf("keys", "earbuds"), YoloeDetector.fit(640, 360, 1f), 640, 360, 0.25f)
        assertEquals(listOf("keys"), found.map { it.label }) // wallet is D-FINE's, earbuds too unsure
        assertEquals("own", found[0].source)
        assertEquals(listOf(95f, 0f, 105f, 0f), found[0].box) // box above the picture clipped to its top edge
    }

    @Test
    fun mergingDropsTheSameThingSeenByBothDetectors() {
        val yolox = listOf(thing("cell phone", 0.6f), thing("chair", 0.7f))
        val dfine = listOf(thing("cell phone", 0.9f), thing("wallet", 0.8f), thing("chair", 0.8f, listOf(100f, 100f, 120f, 120f)))
        assertEquals(listOf("cell phone", "chair", "wallet", "chair"), OptionA.merge(yolox, dfine).map { it.label })
    }

    @Test
    fun theUsersOwnThingsComeFirstInTheCaption() {
        val p = Perception(listOf(thing("desk", 0.9f), thing("cabinet", 0.8f), thing("whiteboard", 0.7f), thing("keys", 0.35f, source = "own")), null, null, 0)
        assertEquals("keys, desk and cabinet", VideoScene.buildCaption(p))
    }

    @Test
    fun personalThingsAreNeverCrowdedOutByFurniture() {
        val p = Perception(listOf(thing("desk", 0.9f), thing("chair", 0.85f), thing("dining table", 0.8f), thing("glasses", 0.6f), thing("wallet", 0.55f), thing("cabinet", 0.5f)), null, null, 1)
        assertEquals("glasses, wallet and desk, 1 person", VideoScene.buildCaption(p))
        val many = Perception(listOf("keys", "wallet", "glasses", "pen").map { thing(it, 0.5f) } + thing("desk", 0.9f), null, null, 0)
        assertEquals("keys, wallet, glasses and pen", VideoScene.buildCaption(many))
    }

    @Test
    fun aVersionJumpRedoesFromTheEarliestChangedStage() {
        assertEquals("dedup", VideoPipeline.redoAfter(1))
        assertEquals("scene", VideoPipeline.redoAfter(2))
        assertEquals("scene", VideoPipeline.redoAfter(3))
        assertEquals(null, VideoPipeline.redoAfter(VideoPipeline.VERSION))
    }

    @Test
    fun objectsSurviveTheDatabaseText() {
        val p = Perception(listOf(thing("keys", 0.4f, source = "own"), thing("chair", 0.7f)), null, null, 0)
        assertEquals(p.objects, VideoScene.objectsFrom(VideoScene.objectsJson(p)))
        assertEquals("detector", VideoScene.objectsFrom("""[{"label":"cup","conf":0.5,"box":[0,0,1,1]}]""").single().source)
    }
}
