package com.eykon.memory.ml.vision

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

/**
 * The Kotlin tokenizer against open_clip's own tokenizer: tokens_golden.json holds the numbers
 * the laptop got for each sentence (written by src/benchmarks/export_clip_text.py).
 */
class ClipTokenizerTest {

    // Unit tests run from the app module's folder, so the app's own asset can be read directly.
    private val tokenizer = ClipTokenizer(File("src/main/assets/clip_bpe_merges.txt").readLines().filter { it.isNotEmpty() })
    private val golden = Json.parseToJsonElement(javaClass.getResource("/clip/tokens_golden.json")!!.readText()).jsonObject

    @Test
    fun everySentenceGivesTheSameNumbersAsTheLaptop() {
        val sentences = golden["sentences"]!!.jsonObject
        assertEquals(10, sentences.size)
        for ((sentence, expected) in sentences) {
            val laptop = expected.jsonArray.map { it.jsonPrimitive.int.toLong() }
            val phone = tokenizer.encode(sentence)
            assertEquals(ClipTokenizer.LENGTH, phone.size)
            assertEquals(sentence, laptop, phone.take(laptop.size))
            assertEquals("$sentence: the rest is zeros", 0L, phone.drop(laptop.size).sum())
        }
    }

    @Test
    fun aPhraseStartsAndEndsWithTheMarkers() {
        val tokens = tokenizer.encode("a helmet").filter { it != 0L }
        assertEquals(ClipTokenizer.START.toLong(), tokens.first())
        assertEquals(ClipTokenizer.END_ID.toLong(), tokens.last())
        assertEquals(4, tokens.size) // start, "a", "helmet", end
    }

    @Test
    fun textThatIsTooLongIsCutAndStillEndsWithTheEndMarker() {
        val tokens = tokenizer.encode("keys ".repeat(200))
        assertEquals(ClipTokenizer.LENGTH, tokens.size)
        assertEquals(ClipTokenizer.END_ID.toLong(), tokens.last())
        assertEquals(0, tokens.count { it == 0L })
    }

    @Test
    fun capitalsAndExtraSpacesDoNotChangeTheResult() {
        assertEquals(tokenizer.encode("where are my keys").toList(), tokenizer.encode("  Where   ARE my\tkeys ").toList())
    }
}
