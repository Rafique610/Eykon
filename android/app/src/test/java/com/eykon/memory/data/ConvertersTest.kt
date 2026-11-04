package com.eykon.memory.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ConvertersTest {

    private lateinit var converters: Converters

    @Before
    fun setup() {
        converters = Converters()
    }

    @Test
    fun testEmbeddingSerializationRoundTrip() {
        // Create a 384-dimensional vector with deterministic float values
        val original = List(384) { index -> (index * 0.005f) - 0.96f }
        val json = converters.toEmbeddingJson(original)

        val restored = converters.fromEmbeddingJson(json)
        assertEquals(384, restored.size)
        for (i in original.indices) {
            assertEquals(original[i], restored[i], 1e-6f)
        }
    }

    @Test
    fun testEmptyListSerialization() {
        val json = converters.toEmbeddingJson(emptyList())
        assertEquals("[]", json)

        val restored = converters.fromEmbeddingJson(json)
        assertTrue(restored.isEmpty())
    }

    @Test
    fun testNullOrBlankHandling() {
        assertEquals("[]", converters.toEmbeddingJson(null))
        assertTrue(converters.fromEmbeddingJson(null).isEmpty())
        assertTrue(converters.fromEmbeddingJson("").isEmpty())
        assertTrue(converters.fromEmbeddingJson("   ").isEmpty())
    }

    @Test
    fun testCorruptedJsonHandling() {
        val corrupt = "[1.0, 2.0, not_a_number"
        val restored = converters.fromEmbeddingJson(corrupt)
        assertTrue(restored.isEmpty())
    }
}
