package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase
import java.io.File
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

    /** How tables are held in memory. HEAP_F32 is the app's way; the rest are EYKO-109 variants (tests set it). */
    @Volatile internal var mode = VectorMode.HEAP_F32

    /** How many of the best int8 scores are re-scored with the exact float32 vector (DIRECT_I8 only). */
    private const val RESCORE = 100

    private class Loaded(val stamp: Pair<Long, Long>, val ids: LongArray, val matrix: FloatArray?, val block: VectorBlock?, val size: Int)

    /** Every row's id (ascending) and its likeness to the query, at the same index. */
    class Scored(val ids: LongArray, val scores: FloatArray)

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
    fun knn(db: SupportSQLiteDatabase, table: String, query: FloatArray, k: Int): List<Pair<Long, Float>> {
        val all = scores(db, table, query)
        val order = rankDescending(all.scores)
        return List(minOf(k, order.size)) { all.ids[order[it]] to all.scores[order[it]] }
    }

    /** Every row's likeness to [query], in id order: no sorting and no boxing (EYKO-102). */
    @Synchronized
    fun scores(db: SupportSQLiteDatabase, table: String, query: FloatArray): Scored {
        val (idColumn, size) = TABLES.getValue(table)
        require(query.size == size) { "$table expects $size numbers, got ${query.size}" }
        val stamp = db.query("SELECT COUNT(*), IFNULL(MAX($idColumn), 0) FROM $table").use { it.moveToFirst(); it.getLong(0) to it.getLong(1) }
        val loaded = cache[table]?.takeIf { it.stamp == stamp } ?: load(db, table, idColumn, size, stamp).also { cache[table] = it }
        val block = loaded.block ?: return Scored(loaded.ids, FloatArray(loaded.ids.size) { row -> dot(loaded.matrix!!, row * size, query) })
        val out = FloatArray(loaded.ids.size)
        block.scoreAll(query, out)
        if (mode == VectorMode.DIRECT_I8) rescore(db, table, idColumn, loaded.ids, out, query)
        return Scored(loaded.ids, out)
    }

    /** Replace the [RESCORE] best int8 scores with the exact float32 likeness, read back by id. */
    private fun rescore(db: SupportSQLiteDatabase, table: String, idColumn: String, ids: LongArray, scores: FloatArray, query: FloatArray) {
        for (row in rankDescending(scores).take(RESCORE)) {
            db.query("SELECT embedding FROM $table WHERE $idColumn = ?", arrayOf(ids[row])).use {
                if (it.moveToFirst()) scores[row] = dot(fromBlob(it.getBlob(0)), 0, query)
            }
        }
    }

    /**
     * The dot product of [query] with the vector starting at [base] in [matrix], with four running
     * sums so the CPU can work on them at once (EYKO-100: same top 20 as one sum on 400 of 400 queries).
     */
    internal fun dot(matrix: FloatArray, base: Int, query: FloatArray): Float {
        var s0 = 0f
        var s1 = 0f
        var s2 = 0f
        var s3 = 0f
        var i = 0
        val end = query.size - query.size % 4
        while (i < end) {
            s0 += matrix[base + i] * query[i]
            s1 += matrix[base + i + 1] * query[i + 1]
            s2 += matrix[base + i + 2] * query[i + 2]
            s3 += matrix[base + i + 3] * query[i + 3]
            i += 4
        }
        while (i < query.size) { s0 += matrix[base + i] * query[i]; i++ }
        return (s0 + s1) + (s2 + s3)
    }

    /**
     * Indexes of [scores] from highest to lowest; equal scores keep their order, the same as
     * `indices.sortedByDescending { scores[it] }`. Each (score, index) is packed into one Long and
     * the Longs are sorted as plain numbers: no comparator and no boxed Integers (EYKO-102).
     */
    internal fun rankDescending(scores: FloatArray): IntArray {
        val packed = LongArray(scores.size) { i ->
            val bits = java.lang.Float.floatToIntBits(scores[i])
            val key = if (bits < 0) bits xor 0x7fffffff else bits // orders like Float.compare
            (key.toLong() shl 32) or (Int.MAX_VALUE - i).toLong() // ties: lower index ranks higher
        }
        packed.sort()
        return IntArray(packed.size) { Int.MAX_VALUE - (packed[packed.size - 1 - it] and 0xffffffffL).toInt() }
    }

    private fun load(db: SupportSQLiteDatabase, table: String, idColumn: String, size: Int, stamp: Pair<Long, Long>): Loaded {
        val rows = stamp.first.toInt()
        val ids = LongArray(rows)
        val block = if (mode == VectorMode.HEAP_F32) null else VectorBlock(mode, rows, size, if (mode == VectorMode.MAPPED_F32) File("${db.path}.$table.vec") else null)
        val matrix = if (block == null) FloatArray(rows * size) else null
        db.query("SELECT $idColumn, embedding FROM $table ORDER BY $idColumn").use { cursor ->
            var row = 0
            while (cursor.moveToNext() && row < rows) {
                ids[row] = cursor.getLong(0)
                if (block != null) block.put(row, cursor.getBlob(1))
                else ByteBuffer.wrap(cursor.getBlob(1)).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(matrix!!, row * size, size)
                row++
            }
        }
        return Loaded(stamp, ids, matrix, block, size)
    }

    internal fun toBlob(vector: FloatArray): ByteArray =
        ByteBuffer.allocate(vector.size * 4).order(ByteOrder.LITTLE_ENDIAN).apply { asFloatBuffer().put(vector) }.array()

    internal fun fromBlob(bytes: ByteArray): FloatArray =
        FloatArray(bytes.size / 4).also { ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(it) }
}
