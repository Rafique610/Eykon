package com.eykon.memory.ml.embedder

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

/**
 * The Kotlin tokenizer against the laptop's bge-small tokenizer: tokens_golden.json holds the
 * numbers the laptop got for each sentence (written by src/benchmarks/export_bge.py).
 */
class WordPieceTokenizerTest {

    // Unit tests run from the app module's folder, so the app's own asset can be read directly.
    private val tokenizer = WordPieceTokenizer(File("src/main/assets/bge_vocab.txt").readLines())
    private val golden = Json.parseToJsonElement(javaClass.getResource("/bge/tokens_golden.json")!!.readText()).jsonObject

    @Test
    fun everySentenceGivesTheSameNumbersAsTheLaptop() {
        val sentences = golden["sentences"]!!.jsonObject
        assertEquals(10, sentences.size)
        for ((sentence, expected) in sentences) {
            assertEquals(sentence, expected.jsonArray.map { it.jsonPrimitive.int.toLong() }, tokenizer.encode(sentence).toList())
        }
    }

    @Test
    fun aSentenceStartsAndEndsWithTheMarkers() {
        val tokens = tokenizer.encode("a laptop")
        assertEquals(listOf(101L, 102L), listOf(tokens.first(), tokens.last()))
        assertEquals(4, tokens.size)
    }

    @Test
    fun textThatIsTooLongIsCutToTheModelsLimit() {
        val tokens = tokenizer.encode("keys ".repeat(1000))
        assertEquals(WordPieceTokenizer.MAX_LENGTH, tokens.size)
        assertEquals(102L, tokens.last())
    }

    @Test
    fun aWordMadeOfUnknownSignsBecomesTheUnknownPiece() {
        assertEquals(listOf(101L, 100L, 102L), tokenizer.encode("☃☃☃").toList()) // three snowmen in a row
    }
}
