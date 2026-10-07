package com.eykon.memory.capture

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.time.Instant

class AudioCaptureTest {

    @Test
    fun testWavHeaderFormatAndConstants() {
        val audioByteCount = 32000L // 1 second of 16kHz 16-bit mono audio
        val header = AudioCaptureService.buildWavHeader(audioByteCount)

        assertEquals(44, header.size)

        val buffer = ByteBuffer.wrap(header).order(ByteOrder.LITTLE_ENDIAN)

        // RIFF header
        val riff = ByteArray(4)
        buffer.get(riff)
        assertEquals("RIFF", String(riff))

        val totalChunkSize = buffer.getInt()
        assertEquals(audioByteCount + 36, totalChunkSize.toLong())

        val wave = ByteArray(4)
        buffer.get(wave)
        assertEquals("WAVE", String(wave))

        // fmt chunk
        val fmt = ByteArray(4)
        buffer.get(fmt)
        assertEquals("fmt ", String(fmt))

        val subchunk1Size = buffer.getInt()
        assertEquals(16, subchunk1Size)

        val audioFormat = buffer.getShort()
        assertEquals(1.toShort(), audioFormat) // 1 = PCM

        val numChannels = buffer.getShort()
        assertEquals(1.toShort(), numChannels) // 1 = Mono

        val sampleRate = buffer.getInt()
        assertEquals(16000, sampleRate)

        val byteRate = buffer.getInt()
        assertEquals(32000, byteRate) // 16000 * 1 * (16 / 8)

        val blockAlign = buffer.getShort()
        assertEquals(2.toShort(), blockAlign) // 1 * (16 / 8)

        val bitsPerSample = buffer.getShort()
        assertEquals(16.toShort(), bitsPerSample)

        // data chunk
        val data = ByteArray(4)
        buffer.get(data)
        assertEquals("data", String(data))

        val dataSize = buffer.getInt()
        assertEquals(audioByteCount, dataSize.toLong())
    }

    @Test
    fun testCreateMemoryFromAudioText() {
        val transcribedText = "Remember to buy groceries on Friday evening"
        val records = TextCaptureService.createMemoriesFromText(
            text = transcribedText,
            sourceType = "audio"
        )

        assertTrue(records.isNotEmpty())
        val record = records.first()

        assertEquals("Remember to buy groceries on Friday evening", record.text)
        assertEquals("audio", record.sourceType)
        assertTrue(record.metadata.contains("chunk_index"))

        val parsed = Instant.parse(record.timestamp)
        assertNotNull(parsed)
    }
}
