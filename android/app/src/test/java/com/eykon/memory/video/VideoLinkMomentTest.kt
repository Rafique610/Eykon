package com.eykon.memory.video

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.Instant

/** The clock time of a point in a video is the recording time plus the seconds into it. */
class VideoLinkMomentTest {

    @Test
    fun aPointInTheVideoIsItsRecordingTimePlusTheSeconds() {
        assertEquals(Instant.parse("2026-10-07T18:42:05Z"), VideoLink.moment("2026-10-07T18:41:23Z", 42.0))
    }

    @Test
    fun partsOfASecondAreKept() {
        assertEquals(Instant.parse("2026-10-07T18:41:23.667Z"), VideoLink.moment("2026-10-07T18:41:23Z", 0.6667))
    }

    @Test
    fun aRecordingTimeWithFractionsAndMidnightBothWork() {
        assertEquals(Instant.parse("2026-10-14T00:00:01.791580Z"), VideoLink.moment("2026-10-13T23:59:44.791580Z", 17.0))
    }
}
