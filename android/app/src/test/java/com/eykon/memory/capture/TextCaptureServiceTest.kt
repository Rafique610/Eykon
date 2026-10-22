package com.eykon.memory.capture

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant

class TextCaptureServiceTest {

    @Test
    fun testValidTextCreatesMemoryRecord() {
        val input = "Dentist appointment next Tuesday at 3pm"
        val record = TextCaptureService.createMemoryFromText(input)

        assertEquals("Dentist appointment next Tuesday at 3pm", record.text)
        assertTrue(record.embedding.isEmpty())
        assertEquals("text", record.sourceType)
        assertTrue(record.metadata.contains("chunk_index"))

        // Ensure timestamp is valid ISO-8601
        val parsed = Instant.parse(record.timestamp)
        assertNotNull(parsed)
    }

    @Test
    fun testTrimsWhitespaceFromInput() {
        val input = "   Call mom this weekend   \n  "
        val record = TextCaptureService.createMemoryFromText(input)
        assertEquals("Call mom this weekend", record.text)
    }

    @Test
    fun testEmptyInputThrowsException() {
        val exception = assertThrows(IllegalArgumentException::class.java) {
            TextCaptureService.createMemoryFromText("")
        }
        assertTrue(exception.message!!.contains("empty or whitespace"))
    }

    @Test
    fun testWhitespaceOnlyInputThrowsException() {
        val exception = assertThrows(IllegalArgumentException::class.java) {
            TextCaptureService.createMemoryFromText("    \t\n  ")
        }
        assertTrue(exception.message!!.contains("empty or whitespace"))
    }
}
