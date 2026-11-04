package com.eykon.memory.data

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room Entity representing a single persistent memory record.
 * Mirrors the validated Phase 1 SQLite schema.
 */
@Entity(tableName = "memories")
data class MemoryRecord(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "text")
    val text: String,

    @ColumnInfo(name = "embedding")
    val embedding: List<Float> = emptyList(),

    @ColumnInfo(name = "timestamp")
    val timestamp: String, // ISO-8601 string, e.g. "2026-09-09T21:30:00"

    @ColumnInfo(name = "source_type", defaultValue = "text")
    val sourceType: String = "text",

    @ColumnInfo(name = "metadata", defaultValue = "{}")
    val metadata: String = "{}"
) {
    val hasEmbedding: Boolean
        get() = embedding.isNotEmpty()
}
