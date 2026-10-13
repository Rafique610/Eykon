package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Vectors in the database, the phone's copy of the laptop's src/video_memory/db.py.
 * A vector is a float32 BLOB (little-endian, the same bytes numpy writes) in a normal table.
 * Search reads a table into memory once and compares with the dot product; vectors have
 * length 1, so the dot product is the cosine. No SQLite extension is used.
 */
object VideoVectors {

    /** table -> (id column, how many numbers a vector has). Fixed names, never user input. */
    private val TABLES = mapOf(
        "image_vec" to ("frame_id" to 512),
        "text_vec" to ("text_id" to 384),
        "audio_vec" to ("window_id" to 512),
    )

    private class Loaded(val stamp: Pair<Long, Long>, val ids: LongArray, val matrix: FloatArray, val size: Int)

    private val cache = HashMap<String, Loaded>()

    /** Store one vector for a row, replacing an earlier one. The caller owns the transaction. */
    @Synchronized
    fun put(db: SupportSQLiteDatabase, table: String, rowId: Long, vector: FloatArray) {
        val (idColumn, size) = TABLES.getValue(table)
        require(vector.size == size) { "$table expects $size numbers, got ${vector.size}" }
        db.execSQL("INSERT OR REPLACE INTO $table ($idColumn, embedding) VALUES (?, ?)", arrayOf(rowId, toBlob(vector)))
        cache.remove(table)
    }

    @Synchronized
    fun clearCache(table: String? = null) {
        if (table == null) cache.clear() else cache.remove(table)
    }

    /** The [k] rows most like [query], best first, as (row id, cosine). */
    @Synchronized
    fun knn(db: SupportSQLiteDatabase, table: String, query: FloatArray, k: Int): List<Pair<Long, Float>> {
        val (idColumn, size) = TABLES.getValue(table)
        require(query.size == size) { "$table expects $size numbers, got ${query.size}" }
        val stamp = db.query("SELECT COUNT(*), IFNULL(MAX($idColumn), 0) FROM $table").use { it.moveToFirst(); it.getLong(0) to it.getLong(1) }
        val loaded = cache[table]?.takeIf { it.stamp == stamp } ?: load(db, table, idColumn, size, stamp).also { cache[table] = it }
        val scores = FloatArray(loaded.ids.size) { row ->
            var sum = 0f
            val base = row * size
            for (i in 0 until size) sum += loaded.matrix[base + i] * query[i]
            sum
        }
        return scores.indices.sortedByDescending { scores[it] }.take(k).map { loaded.ids[it] to scores[it] }
    }

    private fun load(db: SupportSQLiteDatabase, table: String, idColumn: String, size: Int, stamp: Pair<Long, Long>): Loaded {
        val rows = stamp.first.toInt()
        val ids = LongArray(rows)
        val matrix = FloatArray(rows * size)
        db.query("SELECT $idColumn, embedding FROM $table ORDER BY $idColumn").use { cursor ->
            var row = 0
            while (cursor.moveToNext() && row < rows) {
                ids[row] = cursor.getLong(0)
                ByteBuffer.wrap(cursor.getBlob(1)).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(matrix, row * size, size)
                row++
            }
        }
        return Loaded(stamp, ids, matrix, size)
    }

    internal fun toBlob(vector: FloatArray): ByteArray =
        ByteBuffer.allocate(vector.size * 4).order(ByteOrder.LITTLE_ENDIAN).apply { asFloatBuffer().put(vector) }.array()

    internal fun fromBlob(bytes: ByteArray): FloatArray =
        FloatArray(bytes.size / 4).also { ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(it) }
}
