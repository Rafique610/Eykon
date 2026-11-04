package com.eykon.memory.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.time.Instant

class VideoMetadataTest {

    @Test
    fun locationIsReadFromIso6709() {
        val place = VideoMetadata.parseLocation("+24.8607+067.0011/")
        assertEquals(24.8607, place!!.first, 1e-6)
        assertEquals(67.0011, place.second, 1e-6)
    }

    @Test
    fun southAndWestAreNegative() {
        val place = VideoMetadata.parseLocation("-33.8688-151.2093+010.000/")
        assertEquals(-33.8688, place!!.first, 1e-6)
        assertEquals(-151.2093, place.second, 1e-6)
    }

    @Test
    fun missingOrBrokenLocationIsNull() {
        assertNull(VideoMetadata.parseLocation(null))
        assertNull(VideoMetadata.parseLocation(""))
        assertNull(VideoMetadata.parseLocation("somewhere"))
    }

    @Test
    fun recordingTimeIsReadAsUtc() {
        assertEquals(Instant.parse("2026-10-07T18:42:00Z"), VideoMetadata.parseRecordedAt("20261007T184200.000Z"))
        assertEquals(Instant.parse("2026-10-07T18:42:00Z"), VideoMetadata.parseRecordedAt("20261007T184200Z"))
    }

    @Test
    fun theContainerZeroDateCountsAsNoTime() {
        assertNull(VideoMetadata.parseRecordedAt("19040101T000000.000Z"))
    }

    @Test
    fun missingOrBrokenTimeIsNull() {
        assertNull(VideoMetadata.parseRecordedAt(null))
        assertNull(VideoMetadata.parseRecordedAt("yesterday"))
    }

    @Test
    fun onlyTheFourLaptopTypesAreAccepted() {
        assertEquals(setOf("mp4", "mov", "m4v", "avi"), VideoMetadata.TYPES.values.toSet())
        assertNull(VideoMetadata.TYPES["image/jpeg"])
    }
}
