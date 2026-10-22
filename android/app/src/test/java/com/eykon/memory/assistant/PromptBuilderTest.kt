package com.eykon.memory.assistant

import com.eykon.memory.data.MemoryRecord
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PromptBuilderTest {

    @Test
    fun testBuildRagPromptWithMemories() {
        val memories = listOf(
            MemoryRecord(
                id = 1,
                text = "Dentist appointment with Dr. Smith next Tuesday at 3pm",
                timestamp = "2026-09-09T10:00:00"
            ),
            MemoryRecord(
                id = 2,
                text = "I prefer green tea over coffee",
                timestamp = "2026-09-08T12:00:00"
            )
        )
        val prompt = PromptBuilder.buildRagPrompt("When is my dentist appointment?", memories)

        assertTrue(prompt.contains("Guidelines:"))
        assertTrue(prompt.contains("Stored memories:"))
        assertTrue(prompt.contains("[1] Dentist appointment with Dr. Smith next Tuesday at 3pm"))
        assertTrue(prompt.contains("[2] I prefer green tea over coffee"))
        assertTrue(prompt.contains("Question: When is my dentist appointment?"))
        assertTrue(prompt.endsWith("Answer:"))
    }

    @Test
    fun testBuildRagPromptEmptyMemories() {
        val prompt = PromptBuilder.buildRagPrompt("What is my secret code?", emptyList())
        assertTrue(prompt.contains("No relevant memories found."))
        assertTrue(prompt.contains("Question: What is my secret code?"))
    }

    @Test
    fun testGenerationParamsParityWithPhase1() {
        val params = GenerationParams()
        assertEquals(0.3f, params.temperature, 1e-6f)
        assertEquals(256, params.maxOutputTokens)
        assertEquals(40, params.topK)
        assertEquals(0.95f, params.topP, 1e-6f)
    }

    @Test
    fun testCleanAnswerPrefixRemoval() {
        assertEquals("You like tea.", LiteRTGenerator.cleanAnswer("Answer: You like tea."))
        assertEquals("You like tea.", LiteRTGenerator.cleanAnswer("answer: You like tea."))
        assertEquals("You like tea.", LiteRTGenerator.cleanAnswer("  answer:   You like tea.  "))
        assertEquals("You like tea.", LiteRTGenerator.cleanAnswer("You like tea."))
    }
}
