package com.eykon.memory.video

import com.eykon.memory.ml.vision.Detection
import org.junit.Assert.assertEquals
import org.junit.Test

/** The caption is plain words built from the fields. No model is involved. */
class VideoSceneCaptionTest {

    private fun thing(label: String, conf: Float) = Detection(label, conf, listOf(0f, 0f, 1f, 1f))

    @Test
    fun nothingSeenSaysSo() {
        assertEquals("nothing recognised", VideoScene.buildCaption(Perception(emptyList(), null, null, 0)))
    }

    @Test
    fun oneObject() {
        assertEquals("laptop", VideoScene.buildCaption(Perception(listOf(thing("laptop", 0.8f)), null, null, 0)))
    }

    @Test
    fun twoObjectsAndAPlaceLikeTheCardsExample() {
        val seen = Perception(listOf(thing("keys", 0.8f), thing("cell phone", 0.6f)), null, "a hallway", 0)
        assertEquals("keys and cell phone, in a hallway", VideoScene.buildCaption(seen))
    }

    @Test
    fun threeDifferentObjectsSurestFirstAndRepeatsCountOnce() {
        val seen = Perception(
            listOf(thing("chair", 0.5f), thing("laptop", 0.9f), thing("chair", 0.7f), thing("cup", 0.6f), thing("book", 0.4f)),
            null, null, 0,
        )
        assertEquals("laptop, chair and cup", VideoScene.buildCaption(seen))
    }

    @Test
    fun aPlaceThatAlreadySaysInsideIsNotGivenASecondIn() {
        assertEquals("car, 2 people, inside a car", VideoScene.buildCaption(Perception(listOf(thing("car", 0.8f)), null, "inside a car", 2)))
    }

    @Test
    fun peoplePlaceAndAction() {
        assertEquals("1 person, in an office, typing on a laptop", VideoScene.buildCaption(Perception(emptyList(), "typing on a laptop", "an office", 1)))
        assertEquals("laptop, 3 people, in a classroom, reading", VideoScene.buildCaption(Perception(listOf(thing("laptop", 0.8f)), "reading", "a classroom", 3)))
    }
}
