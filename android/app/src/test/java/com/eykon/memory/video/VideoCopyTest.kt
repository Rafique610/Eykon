package com.eykon.memory.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.ByteArrayInputStream
import java.io.IOException
import java.io.InputStream

/** EYKO-71: the hash taken while copying, and the refusals when the file is too big or the phone too full. */
class VideoCopyTest {

    @get:Rule
    val folder = TemporaryFolder()

    private val plentyOfSpace = { 10L * 1024 * 1024 * 1024 }
    private val oneMb = 1024L * 1024

    @Test
    fun theHashIsTheSha256OfTheBytesAndTheFileIsAnExactCopy() {
        val target = folder.newFile("a.mp4")
        val result = VideoCopy.copyAndHash(ByteArrayInputStream("abc".toByteArray()), target, 10 * oneMb, plentyOfSpace)
        // the published SHA-256 test vector for "abc"
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", result.sha256)
        assertEquals(3L, result.bytes)
        assertEquals("abc", target.readText())
    }

    @Test
    fun theSameBytesGiveTheSameHashAndOtherBytesGiveAnotherOne() {
        val data = ByteArray(300_000) { (it % 251).toByte() }
        val first = VideoCopy.copyAndHash(ByteArrayInputStream(data), folder.newFile("1.mp4"), 10 * oneMb, plentyOfSpace)
        val again = VideoCopy.copyAndHash(ByteArrayInputStream(data), folder.newFile("2.mp4"), 10 * oneMb, plentyOfSpace)
        val other = VideoCopy.copyAndHash(ByteArrayInputStream(data.copyOf().also { it[299_999] = 7 }), folder.newFile("3.mp4"), 10 * oneMb, plentyOfSpace)
        assertEquals(first.sha256, again.sha256)
        assertNotEquals(first.sha256, other.sha256)
        assertTrue("the hash time is part of the copy time", first.hashMs <= first.copyMs)
    }

    @Test
    fun aFileOverTheLimitIsRefusedAndNoHalfCopyIsLeft() {
        val target = folder.newFile("big.mp4")
        try {
            VideoCopy.copyAndHash(ByteArrayInputStream(ByteArray(3 * oneMb.toInt())), target, 2 * oneMb, plentyOfSpace)
            fail("expected a refusal")
        } catch (e: UploadException) {
            assertEquals("This file is larger than the limit of 2 MB.", e.message)
        }
        assertFalse(target.exists())
    }

    @Test
    fun aKnownSizeThatDoesNotFitIsRefusedBeforeAnyCopying() {
        val message = VideoCopy.roomProblem(sizeBytes = 400 * oneMb, freeBytes = 500 * oneMb)
        assertTrue(message!!.startsWith("Not enough free space"))
        assertTrue(message.contains("600 MB")) // 400 MB video + the 200 MB reserve
        assertTrue(message.contains("500 MB free"))
        assertNull(VideoCopy.roomProblem(sizeBytes = 400 * oneMb, freeBytes = 700 * oneMb))
    }

    @Test
    fun anUnknownSizeIsOnlyRefusedWhenThePhoneIsAlreadyBelowTheReserve() {
        assertNull(VideoCopy.roomProblem(sizeBytes = null, freeBytes = 300 * oneMb))
        assertTrue(VideoCopy.roomProblem(sizeBytes = null, freeBytes = 100 * oneMb)!!.startsWith("The phone is almost full"))
    }

    @Test
    fun theCopyStopsWhenTheSpaceRunsLowPartWayAndLeavesNoFile() {
        val target = folder.newFile("filling.mp4")
        var free = 1000 * oneMb
        val shrinking = { free.also { free -= 200 * oneMb } } // each 8 MB check sees 200 MB less: 1000, 800 ... 200, then 0
        try {
            VideoCopy.copyAndHash(ByteArrayInputStream(ByteArray(60 * oneMb.toInt())), target, 500 * oneMb, shrinking)
            fail("expected a refusal")
        } catch (e: UploadException) {
            assertTrue(e.message!!.startsWith("The phone is almost full"))
        }
        assertFalse(target.exists())
    }

    @Test
    fun aDiskFullErrorFromTheFileSystemBecomesAClearMessageAndLeavesNoFile() {
        val target = folder.newFile("full.mp4")
        val failing = object : InputStream() {
            private var sent = false
            override fun read(): Int = throw IOException("write failed: ENOSPC (No space left on device)")
            override fun read(b: ByteArray, off: Int, len: Int): Int {
                if (!sent) { sent = true; return 10 }
                throw IOException("write failed: ENOSPC (No space left on device)")
            }
        }
        try {
            VideoCopy.copyAndHash(failing, target, 10 * oneMb, plentyOfSpace)
            fail("expected a refusal")
        } catch (e: UploadException) {
            assertTrue(e.message!!.startsWith("The phone ran out of space"))
        }
        assertFalse(target.exists())
    }
}
