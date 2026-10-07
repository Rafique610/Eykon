package com.eykon.memory.ui.viewmodels

import androidx.sqlite.db.SupportSQLiteQuery
import com.eykon.memory.assistant.GenerationResult
import com.eykon.memory.assistant.ModelManager
import com.eykon.memory.data.MemoryDao
import com.eykon.memory.data.MemoryRecord
import com.eykon.memory.retrieval.SearchService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AskQuestionViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var fakeDao: FakeMemoryDao
    private lateinit var searchService: SearchService
    private lateinit var viewModel: AskQuestionViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        fakeDao = FakeMemoryDao()
        searchService = SearchService(fakeDao)

        viewModel = AskQuestionViewModel(
            dao = fakeDao,
            searchService = searchService,
            modelStatusProvider = {
                ModelManager.ModelStatus(
                    isAvailable = true,
                    filePath = "/mock/gemma-4.litertlm",
                    sizeBytes = 2500000000L,
                    targetDirectory = "/mock",
                    adbPushCommand = ""
                )
            },
            answerGenerator = { question, memories ->
                GenerationResult(
                    answer = "Synthesized response for '$question' based on ${memories.size} memories.",
                    latencyMs = 450L,
                    isModelFound = true,
                    fullPrompt = "test prompt"
                )
            },
            ioDispatcher = testDispatcher,
            defaultDispatcher = testDispatcher
        )
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testInitialState() = runTest {
        advanceUntilIdle()
        val state = viewModel.uiState.value
        assertEquals("", state.query)
        assertFalse(state.isLoading)
        assertNull(state.answer)
        assertTrue(state.modelStatus.isAvailable)
    }

    @Test
    fun testOnQueryChanged() = runTest {
        viewModel.onQueryChanged("When is my meeting?")
        val state = viewModel.uiState.value
        assertEquals("When is my meeting?", state.query)
        assertNull(state.errorMessage)
    }

    @Test
    fun testAskQuestionBlankFailsValidation() = runTest {
        viewModel.onQueryChanged("   ")
        viewModel.askQuestion()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertNotNull(state.errorMessage)
        assertNull(state.answer)
        assertFalse(state.isLoading)
    }

    @Test
    fun testAskQuestionSuccess_retrievesAndSynthesizesAnswer() = runTest {
        fakeDao.insert(
            MemoryRecord(
                id = 1,
                text = "Dentist appointment is on Tuesday at 3pm.",
                timestamp = "2026-10-02T10:00:00"
            )
        )
        advanceUntilIdle()

        viewModel.askQuestion("When is my dentist appointment?")
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.isLoading)
        assertNull(state.errorMessage)
        assertNotNull(state.answer)
        assertTrue(state.answer!!.contains("Synthesized response"))
        assertEquals(1, state.retrievedMemories.size)
        assertEquals(1L, state.retrievedMemories.first().first.id)
        assertEquals(450L, state.latencyMs)
    }

    @Test
    fun testOnSpeechResult_autoSubmitsQuery() = runTest {
        fakeDao.insert(
            MemoryRecord(
                id = 2,
                text = "My flight to Tokyo is on December 15th.",
                timestamp = "2026-10-02T10:00:00"
            )
        )
        advanceUntilIdle()

        viewModel.onSpeechResult("When is my flight?")
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertEquals("When is my flight?", state.query)
        assertNotNull(state.answer)
        assertEquals(1, state.retrievedMemories.size)
    }

    private class FakeMemoryDao : MemoryDao {
        val records = mutableListOf<MemoryRecord>()
        private val flow = MutableStateFlow<List<MemoryRecord>>(emptyList())

        override suspend fun insert(record: MemoryRecord): Long {
            val id = if (record.id == 0L) (records.size + 1).toLong() else record.id
            val saved = record.copy(id = id)
            records.add(saved)
            flow.value = records.toList()
            return id
        }

        override suspend fun insertAll(records: List<MemoryRecord>): List<Long> =
            records.map { insert(it) }

        override suspend fun getAll(): List<MemoryRecord> = records.toList()
        override fun getAllAsFlow(): Flow<List<MemoryRecord>> = flow.asStateFlow()
        override suspend fun getById(id: Long): MemoryRecord? = records.find { it.id == id }
        override suspend fun deleteById(id: Long): Int {
            val removed = records.removeIf { it.id == id }
            flow.value = records.toList()
            return if (removed) 1 else 0
        }
        override suspend fun count(): Int = records.size
        override suspend fun deleteAll(): Int {
            val count = records.size
            records.clear()
            flow.value = emptyList()
            return count
        }
        override suspend fun update(record: MemoryRecord): Int = 0

        override suspend fun searchFtsRaw(query: SupportSQLiteQuery): List<MemoryRecord> = emptyList()

        override suspend fun searchFts(query: String, limit: Int): List<MemoryRecord> {
            val queryTerms = query.split(" OR ")
                .map { it.trim().removeSuffix("*").lowercase() }
                .filter { it.isNotBlank() }

            return records.filter { record ->
                val lower = record.text.lowercase()
                queryTerms.any { term -> lower.contains(term) }
            }.take(limit)
        }
    }
}
