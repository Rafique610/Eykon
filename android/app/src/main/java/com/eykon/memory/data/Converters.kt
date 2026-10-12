package com.eykon.memory.data

import androidx.room.TypeConverter
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/**
 * Room TypeConverters to serialize complex structures into SQLite TEXT columns,
 * maintaining 1:1 schema compatibility with Phase 1 SQLite database.
 */
class Converters {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
    }

    @TypeConverter
    fun fromEmbeddingJson(value: String?): List<Float> {
        if (value.isNullOrBlank()) return emptyList()
        return try {
            json.decodeFromString<List<Float>>(value)
        } catch (_: Exception) {
            emptyList()
        }
    }

    @TypeConverter
    fun toEmbeddingJson(list: List<Float>?): String {
        if (list.isNullOrEmpty()) return "[]"
        return json.encodeToString(list)
    }
}
