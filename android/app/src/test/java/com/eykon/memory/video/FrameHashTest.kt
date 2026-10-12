package com.eykon.memory.video

import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Random

class FrameHashTest {

    @Test
    fun everyPictureHashesTheSameAsOpenCv() {
        for ((name, expected) in TestPictures.golden["pictures"]!!.jsonObject) {
            val want = expected.jsonObject["dhash"]!!.jsonPrimitive.content
            assertEquals(name, want, FrameHash.toHex(FrameHash.dHash(TestPictures.picture(name))))
        }
    }

    @Test
    fun everyPairIsAsFarApartAsOpenCvSays() {
        for ((name, expected) in TestPictures.golden["pairs"]!!.jsonObject) {
            val (first, second) = name.split("_vs_").map { FrameHash.dHash(TestPictures.picture(it)) }
            assertEquals(name, expected.jsonObject["hash_distance"]!!.jsonPrimitive.int, FrameHash.distance(first, second))
        }
    }

    private fun noise(seed: Long): Gray {
        val random = Random(seed)
        // big soft blobs, so the 9x8 picture has real structure
        val blobs = IntArray(9 * 8) { random.nextInt(256) }
        return Gray(320, 180, IntArray(320 * 180) { i -> blobs[(i / 320) * 8 / 180 * 9 + (i % 320) * 9 / 320] })
    }

    @Test
    fun theSamePictureHasDistanceZero() {
        assertEquals(0, FrameHash.distance(FrameHash.dHash(noise(1)), FrameHash.dHash(noise(1))))
    }

    @Test
    fun aSlightlyBrighterCopyHashesTheSame() {
        val picture = noise(1)
        val brighter = Gray(picture.width, picture.height, IntArray(picture.pixels.size) { minOf(255, picture.pixels[it] + 3) })
        assertTrue(FrameHash.distance(FrameHash.dHash(picture), FrameHash.dHash(brighter)) <= 2)
    }

    @Test
    fun differentPicturesAreFarApart() {
        assertTrue(FrameHash.distance(FrameHash.dHash(noise(1)), FrameHash.dHash(noise(2))) > 12)
    }

    @Test
    fun theHashIsWrittenAsSixteenHexCharacters() {
        assertEquals("0000000000000000", FrameHash.toHex(0L))
        assertEquals("ffffffffffffffff", FrameHash.toHex(-1L))
        assertEquals(16, FrameHash.toHex(FrameHash.dHash(noise(1))).length)
    }
}
