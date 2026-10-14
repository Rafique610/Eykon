package com.eykon.memory.video

import com.eykon.memory.ml.vision.Detection
import com.eykon.memory.ml.vision.DfineDetector
import com.eykon.memory.ml.vision.ImagePrep
import com.eykon.memory.ml.vision.OwlDetector
import org.junit.Assert.assertEquals
import org.junit.Test

/** The plain maths of D-FINE, OWLv2 and the "small_objects" stage (card EYKO-32). The models run in DetectorGoldenTest on a phone. */
class SmallObjectsTest {

    private fun thing(label: String, conf: Float, box: List<Float> = listOf(0f, 0f, 10f, 10f), source: String = "detector") = Detection(label, conf, box, source)

    @Test
    fun stretchingKeepsColoursAsZeroToOne() {
        val red = 0xFFFF0000.toInt()
        val planes = ImagePrep.rgbPlanes(IntArray(8 * 4) { red }, 8, 4, 4)
        assertEquals(listOf(1f, 0f, 0f), listOf(planes[5], planes[16 + 5], planes[32 + 5]))
    }

    @Test
    fun paddingPutsThePictureTopLeftOnBlack() {
        val white = 0xFFFFFFFF.toInt()
        val planes = ImagePrep.rgbPlanes(IntArray(4 * 2) { white }, 4, 2, 4, padTo = 4)
        assertEquals(1f, planes[0 * 4 + 1], 1e-6f) // row 0 is picture
        assertEquals(0f, planes[3 * 4 + 1], 1e-6f) // row 3 is padding
    }

    @Test
    fun objects365NamesBecomePlainWords() {
        assertEquals(listOf("wallet", "pen", "cell phone", "earphone"), listOf("Wallet/Purse", "Pen/Pencil", "Cell Phone", "earphone").map(DfineDetector::plain))
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
    fun owlGivesOneBoxPerPhraseInsideThePicture() {
        val logits = arrayOf(floatArrayOf(2f, -9f), floatArrayOf(0f, -9f))
        val boxes = arrayOf(floatArrayOf(0.5f, 0.5f, 0.25f, 0.25f), floatArrayOf(0.9f, 0.9f, 0.5f, 0.5f))
        val found = OwlDetector.decode(logits, boxes, listOf("keys", "earbuds"), 640, 640, 360, 0.3f)
        assertEquals(listOf("keys"), found.map { it.label })
        assertEquals("owl", found[0].source)
        assertEquals(listOf(240f, 240f, 400f, 360f), found[0].box) // bottom clipped to the picture
    }

    @Test
    fun mergingDropsTheSameThingSeenByBothDetectors() {
        val yolox = listOf(thing("cell phone", 0.6f), thing("chair", 0.7f))
        val dfine = listOf(thing("cell phone", 0.9f), thing("wallet", 0.8f), thing("chair", 0.8f, listOf(100f, 100f, 120f, 120f)))
        assertEquals(listOf("cell phone", "chair", "wallet", "chair"), OptionA.merge(yolox, dfine).map { it.label })
    }

    @Test
    fun theUsersOwnThingsComeFirstInTheCaption() {
        val p = Perception(listOf(thing("desk", 0.9f), thing("cabinet", 0.8f), thing("whiteboard", 0.7f), thing("keys", 0.35f, source = "owl")), null, null, 0)
        assertEquals("keys, desk and cabinet", VideoScene.buildCaption(p))
    }

    @Test
    fun objectsSurviveTheDatabaseText() {
        val p = Perception(listOf(thing("keys", 0.4f, source = "owl"), thing("chair", 0.7f)), null, null, 0)
        assertEquals(p.objects, VideoScene.objectsFrom(VideoScene.objectsJson(p)))
        assertEquals("detector", VideoScene.objectsFrom("""[{"label":"cup","conf":0.5,"box":[0,0,1,1]}]""").single().source)
    }

    @Test
    fun oneFrameInThreeIsPickedByLikeness() {
        val frames = (1L..6L).toList()
        val vectors = frames.associateWith { floatArrayOf(it.toFloat(), 0f) } + (7L to floatArrayOf(0f, 9f))
        assertEquals(setOf(6L, 5L), VideoSmallObjects.picked(frames, vectors, listOf(floatArrayOf(1f, 0f))))
        assertEquals(setOf(1L), VideoSmallObjects.picked(listOf(1L), emptyMap(), listOf(floatArrayOf(1f, 0f))))
    }
}
