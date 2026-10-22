package com.eykon.memory.retrieval

import androidx.sqlite.db.SupportSQLiteQuery
import com.eykon.memory.data.MemoryDao
import com.eykon.memory.data.MemoryRecord
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class SearchServiceTest {

    private lateinit var fakeDao: FakeMemoryDao
    private lateinit var searchService: SearchService

    @Before
    fun setUp() {
        fakeDao = FakeMemoryDao()
        searchService = SearchService(fakeDao)
    }

    @Test
    fun search_emptyDatabase_returnsEmptyList() = runTest {
        val results = searchService.search("When is my dentist appointment?")
        assertTrue(results.isEmpty())
    }

    @Test
    fun search_withMatchingMemory_returnsRankedResults() = runTest {
        val mem1 = MemoryRecord(
            id = 1,
            text = "Dentist appointment scheduled for next Tuesday at 3pm.",
            timestamp = "2026-10-02T10:00:00"
        )
        val mem2 = MemoryRecord(
            id = 2,
            text = "Had lunch at Subway today.",
            timestamp = "2026-10-02T12:00:00"
        )
        fakeDao.insert(mem1)
        fakeDao.insert(mem2)

        val results = searchService.search("When is my dentist appointment?")

        assertTrue(results.isNotEmpty())
        assertEquals(1L, results.first().first.id)
        assertTrue(results.first().second > 0f)
    }

    @Test
    fun search_withExpandedConcept_retrievesRelevantRecord() = runTest {
        val mem = MemoryRecord(
            id = 10,
            text = "Received 15000 rupees allowance in my bank account.",
            timestamp = "2026-10-02T10:00:00"
        )
        fakeDao.insert(mem)

        // Query contains "financial", QueryExpander expands to include "money rupees allowance..."
        val results = searchService.search("What is my financial status?")

        assertTrue(results.isNotEmpty())
        assertEquals(10L, results.first().first.id)
    }

    @Test
    fun search_specialPunctuationInQuery_doesNotCrash() = runTest {
        fakeDao.insert(
            MemoryRecord(
                id = 5,
                text = "Car is parked on level 2.",
                timestamp = "2026-10-02T10:00:00"
            )
        )

        // Contains quotes, question marks, asterisks, brackets
        val results = searchService.search("Where is my car? 'level 2'* (urgent!)")
        assertNotNull(results)
    }

    private class FakeMemoryDao : MemoryDao {
        private val storage = mutableListOf<MemoryRecord>()

        override suspend fun insert(record: MemoryRecord): Long {
            val id = if (record.id == 0L) (storage.size + 1).toLong() else record.id
            val stored = record.copy(id = id)
            storage.removeAll { it.id == id }
            storage.add(stored)
            return id
        }

        override suspend fun insertAll(records: List<MemoryRecord>): List<Long> {
            return records.map { insert(it) }
        }

        override suspend fun getAll(): List<MemoryRecord> = storage.toList()

        override fun getAllAsFlow(): Flow<List<MemoryRecord>> = flowOf(storage.toList())

        override suspend fun getById(id: Long): MemoryRecord? = storage.find { it.id == id }

        override suspend fun deleteById(id: Long): Int {
            val removed = storage.removeAll { it.id == id }
            return if (removed) 1 else 0
        }

        override suspend fun count(): Int = storage.size

        override suspend fun deleteAll(): Int {
            val size = storage.size
            storage.clear()
            return size
        }

        override suspend fun update(record: MemoryRecord): Int {
            val index = storage.indexOfFirst { it.id == record.id }
            if (index >= 0) {
                storage[index] = record
                return 1
            }
            return 0
        }

        override suspend fun searchFtsRaw(query: SupportSQLiteQuery): List<MemoryRecord> {
            return emptyList()
        }

        override suspend fun searchFts(query: String, limit: Int): List<MemoryRecord> {
            // Emulate FTS token matching for testing
            val queryTerms = query.split(" OR ")
                .map { it.trim().removeSuffix("*").lowercase() }
                .filter { it.isNotBlank() }

            return storage.filter { record ->
                val lower = record.text.lowercase()
                queryTerms.any { term -> lower.contains(term) }
            }.take(limit)
        }
    }
}
