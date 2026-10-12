package com.eykon.memory.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for memories in SQLite database.
 * Provides coroutine suspend methods and reactive Flow observation.
 */
@Dao
interface MemoryDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(record: MemoryRecord): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(records: List<MemoryRecord>): List<Long>

    @Query("SELECT * FROM memories ORDER BY timestamp DESC")
    suspend fun getAll(): List<MemoryRecord>

    @Query("SELECT * FROM memories ORDER BY timestamp DESC")
    fun getAllAsFlow(): Flow<List<MemoryRecord>>

    @Query("SELECT * FROM memories WHERE id = :id")
    suspend fun getById(id: Long): MemoryRecord?

    @Query("DELETE FROM memories WHERE id = :id")
    suspend fun deleteById(id: Long): Int

    @Query("SELECT COUNT(*) FROM memories")
    suspend fun count(): Int

    @Query("DELETE FROM memories")
    suspend fun deleteAll(): Int

    @Update
    suspend fun update(record: MemoryRecord): Int

    @androidx.room.RawQuery
    suspend fun searchFtsRaw(query: androidx.sqlite.db.SupportSQLiteQuery): List<MemoryRecord>

    suspend fun searchFts(query: String, limit: Int): List<MemoryRecord> {
        return try {
            val statement = "SELECT memories.* FROM memories JOIN memories_fts ON memories.id = memories_fts.rowid WHERE memories_fts MATCH ? LIMIT ?"
            searchFtsRaw(androidx.sqlite.db.SimpleSQLiteQuery(statement, arrayOf(query, limit)))
        } catch (e: Exception) {
            emptyList()
        }
    }
}
