package com.eykon.memory.ui.viewmodels

import com.eykon.memory.data.MemoryDao
import com.eykon.memory.data.MemoryRecord
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
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AddMemoryViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var fakeDao: FakeMemoryDao
    private lateinit var viewModel: AddMemoryViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        fakeDao = FakeMemoryDao()
        viewModel = AddMemoryViewModel(fakeDao)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testSaveMemorySuccess() = runTest {
        viewModel.onInputTextChanged("Doctor appointment on Friday")
        viewModel.saveMemory()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertEquals("", state.inputText)
        assertNotNull(state.savedMessage)
        assertNull(state.errorMessage)
        assertEquals(1, fakeDao.records.size)
        assertEquals("Doctor appointment on Friday", fakeDao.records[0].text)
    }

    @Test
    fun testSaveMemoryEmptyFailsValidation() = runTest {
        viewModel.onInputTextChanged("   ")
        viewModel.saveMemory()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertNotNull(state.errorMessage)
        assertNull(state.savedMessage)
        assertEquals(0, fakeDao.records.size)
    }

    private class FakeMemoryDao : MemoryDao {
        val records = mutableListOf<MemoryRecord>()
        private val flow = MutableStateFlow<List<MemoryRecord>>(emptyList())

        override suspend fun insert(record: MemoryRecord): Long {
            val id = (records.size + 1).toLong()
            val saved = record.copy(id = id)
            records.add(saved)
            flow.value = records.toList()
            return id
        }

        override suspend fun insertAll(records: List<MemoryRecord>): List<Long> {
            return records.map { insert(it) }
        }

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
        override suspend fun update(record: MemoryRecord): Int {
            val index = records.indexOfFirst { it.id == record.id }
            if (index != -1) {
                records[index] = record
                flow.value = records.toList()
                return 1
            }
            return 0
        }
    }
}
