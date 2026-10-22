package com.eykon.memory.video

import org.junit.Assert.assertArrayEquals
import org.junit.Test

/** A stored vector must be the same bytes the laptop's numpy writes: float32, little-endian. */
class VideoVectorsBlobTest {

    @Test
    fun aVectorIsStoredAsLittleEndianFloat32() {
        // 1.0f is 0x3F800000 and -2.0f is 0xC0000000; little-endian puts the low byte first
        val expected = byteArrayOf(0x00, 0x00, 0x80.toByte(), 0x3F, 0x00, 0x00, 0x00, 0xC0.toByte())
        assertArrayEquals(expected, VideoVectors.toBlob(floatArrayOf(1f, -2f)))
    }

    @Test
    fun readingBackGivesTheSameNumbers() {
        val vector = floatArrayOf(0.25f, -0.5f, 3.1415927f, 0f)
        assertArrayEquals(vector, VideoVectors.fromBlob(VideoVectors.toBlob(vector)), 0f)
    }
}
