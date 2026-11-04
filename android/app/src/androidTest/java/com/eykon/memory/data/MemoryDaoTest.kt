package com.eykon.memory.data

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.IOException

@RunWith(AndroidJUnit4::class)
class MemoryDaoTest {

    private lateinit var db: MemoryDatabase
    private lateinit var dao: MemoryDao

    @Before
    fun createDb() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        db = Room.inMemoryDatabaseBuilder(context, MemoryDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        dao = db.memoryDao()
    }

    @After
    @Throws(IOException::class)
    fun closeDb() {
        db.close()
    }

    @Test
    fun insertAndGetById() = runBlocking {
        val record = MemoryRecord(
            text = "Had a team meeting at 10 AM",
            embedding = List(384) { 0.05f },
            timestamp = "2026-09-09T10:00:00",
            sourceType = "text",
            metadata = "{\"chunk_index\": 0}"
        )
        val id = dao.insert(record)
        val retrieved = dao.getById(id)

        assertNotNull(retrieved)
        assertEquals("Had a team meeting at 10 AM", retrieved!!.text)
        assertEquals(384, retrieved.embedding.size)
        assertEquals("text", retrieved.sourceType)
        assertEquals(1, dao.count())
    }

    @Test
    fun insertAllAndGetAllOrderedByTimestamp() = runBlocking {
        val r1 = MemoryRecord(
            text = "Old note",
            embedding = emptyList(),
            timestamp = "2026-09-01T08:00:00"
        )
        val r2 = MemoryRecord(
            text = "Recent note",
            embedding = emptyList(),
            timestamp = "2026-09-09T08:00:00"
        )
        val r3 = MemoryRecord(
            text = "Middle note",
            embedding = emptyList(),
            timestamp = "2026-09-05T08:00:00"
        )

        dao.insertAll(listOf(r1, r2, r3))
        val all = dao.getAll()

        assertEquals(3, all.size)
        // Should be ordered by timestamp DESC
        assertEquals("Recent note", all[0].text)
        assertEquals("Middle note", all[1].text)
        assertEquals("Old note", all[2].text)
    }

    @Test
    fun deleteByIdAndCount() = runBlocking {
        val record = MemoryRecord(
            text = "To be deleted",
            embedding = emptyList(),
            timestamp = "2026-09-09T12:00:00"
        )
        val id = dao.insert(record)
        assertEquals(1, dao.count())

        val deletedRows = dao.deleteById(id)
        assertEquals(1, deletedRows)
        assertEquals(0, dao.count())
        assertNull(dao.getById(id))
    }

    @Test
    fun deleteAll() = runBlocking {
        val records = listOf(
            MemoryRecord(text = "Note 1", embedding = emptyList(), timestamp = "2026-09-09T01:00:00"),
            MemoryRecord(text = "Note 2", embedding = emptyList(), timestamp = "2026-09-09T02:00:00")
        )
        dao.insertAll(records)
        assertEquals(2, dao.count())

        dao.deleteAll()
        assertEquals(0, dao.count())
    }
}
