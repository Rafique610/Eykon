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

    /**
     * How tables are held in memory. Since EYKO-115 the app uses MAPPED_NATIVE: a vector file next to the
     * database, mapped and scored in place by libeykonvec.so (EYKO-114: bit-identical, Java memory near zero).
     * If the library does not load, it falls back to HEAP_F32. Tests set other EYKO-109 modes.
     */
    @Volatile internal var mode = if (runCatching { VectorNative.hashCode() }.isSuccess) VectorMode.MAPPED_NATIVE else VectorMode.HEAP_F32

    /** How many of the best int8 scores are re-scored with the exact float32 vector (DIRECT_I8 only). */
    private const val RESCORE = 100

    /** [stamp] is the table's MAX(id) when loaded; [mode] the way it is held (a test may switch modes). */
    private class Loaded(val stamp: Long, val mode: VectorMode, val ids: LongArray, val matrix: FloatArray?, val block: VectorBlock?, val size: Int)

    /** Every row's id (ascending) and its likeness to the query, at the same index. */
    class Scored(val ids: LongArray, val scores: FloatArray)

    /** Keyed by database file and table, so two databases with the same table names never share a copy. */
    private val cache = HashMap<String, Loaded>()

    private fun key(db: SupportSQLiteDatabase, table: String) = "${db.path}|$table"

    /** A database in a file can have a vector file next to it; an in-memory one (tests) uses the heap instead. */
    private fun onDisk(db: SupportSQLiteDatabase) = db.path.let { it != null && it != ":memory:" && it.isNotEmpty() }

    /** The vector file (float32 rows) and its id file (int64), next to the database (EYKO-115). */
    private fun files(db: SupportSQLiteDatabase, table: String) = File("${db.path}.$table.vec") to File("${db.path}.$table.ids")

    /**
     * Store one vector for a row, replacing an earlier one. The caller owns the transaction. A new row
     * (id above every stored id) is appended to the vector file at the next search. Replacing an existing
     * row must follow a delete that called [forget].
     */
    @Synchronized
    fun put(db: SupportSQLiteDatabase, table: String, rowId: Long, vector: FloatArray) {
        val (idColumn, size) = TABLES.getValue(table)
        require(vector.size == size) { "$table expects $size numbers, got ${vector.size}" }
        db.execSQL("INSERT OR REPLACE INTO $table ($idColumn, embedding) VALUES (?, ?)", arrayOf(rowId, toBlob(vector)))
        cache.remove(key(db, table))
    }

    /** Rows were deleted from [table]: drop the copy in memory and the vector file, so the next search rebuilds it. */
    @Synchronized
    fun forget(db: SupportSQLiteDatabase, table: String) {
        cache.remove(key(db, table))
        files(db, table).toList().forEach { it.delete() }
    }

    /** Drop the copies in memory (all tables, or every database's [table]); vector files stay. */
    @Synchronized
    fun clearCache(table: String? = null) {
        if (table == null) cache.clear() else cache.keys.removeAll { it.endsWith("|$table") }
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
        // EYKO-115: MAX(id) reads one path of the key (0.13 ms at 100k); COUNT(*) read the whole table (479 ms).
        // Writes and deletes drop the cache themselves (put, forget, clearCache).
        val stamp = db.query("SELECT IFNULL(MAX($idColumn), 0) FROM $table").use { it.moveToFirst(); it.getLong(0) }
        val k = key(db, table)
        val loaded = cache[k]?.takeIf { it.stamp == stamp && it.mode == mode }
            ?: (if (mode.mapped && onDisk(db)) loadMapped(db, table, idColumn, size, stamp) else load(db, table, idColumn, size, stamp)).also { cache[k] = it }
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

    /**
     * EYKO-115: the vector file is written once and appended to. If it ends at the table's MAX(id) it is
     * only mapped; if the table has newer rows, only those are read (`WHERE id > last`) and appended; if the
     * table ends lower (rows deleted without [forget]) or the two files disagree (a crash mid-append), it is rebuilt.
     */
    private fun loadMapped(db: SupportSQLiteDatabase, table: String, idColumn: String, size: Int, maxId: Long): Loaded {
        val (vecFile, idsFile) = files(db, table)
        val rowBytes = size * 4L
        var ids = if (idsFile.exists() && vecFile.length() == idsFile.length() / 8 * rowBytes) readIds(idsFile) else LongArray(0)
        if (ids.isNotEmpty() && (ids.last() > maxId || !sameRows(db, table, idColumn, vecFile, ids, rowBytes.toInt()))) ids = LongArray(0)
        if (ids.isEmpty()) { vecFile.delete(); idsFile.delete() }
        val last = if (ids.isEmpty()) Long.MIN_VALUE else ids.last()
        if (last < maxId) {
            val added = ArrayList<Long>()
            java.io.FileOutputStream(vecFile, true).buffered(1 shl 20).use { vec ->
                db.query("SELECT $idColumn, embedding FROM $table WHERE $idColumn > ? ORDER BY $idColumn", arrayOf(last)).use { c ->
                    while (c.moveToNext()) { added += c.getLong(0); vec.write(c.getBlob(1), 0, rowBytes.toInt()) }
                }
            }
            // ids are written after the vectors, so a crash leaves files of different lengths and the next load rebuilds
            java.io.FileOutputStream(idsFile, true).buffered(1 shl 16).use { out ->
                val bytes = ByteBuffer.allocate(added.size * 8).order(ByteOrder.LITTLE_ENDIAN)
                added.forEach { bytes.putLong(it) }
                out.write(bytes.array())
            }
            ids = ids + added.toLongArray()
        }
        val block = if (ids.isEmpty()) null else VectorBlock(mode, ids.size, size, vecFile, readOnly = true)
        return Loaded(maxId, mode, ids, if (block == null) FloatArray(0) else null, block, size)
    }

    /**
     * The file's first and last rows still match the database (two lookups by id). Catches a database that
     * was deleted and made again under the same name, which leaves an old vector file behind.
     */
    private fun sameRows(db: SupportSQLiteDatabase, table: String, idColumn: String, vecFile: File, ids: LongArray, rowBytes: Int): Boolean =
        java.io.RandomAccessFile(vecFile, "r").use { file ->
            listOf(0, ids.size - 1).all { row ->
                val inFile = ByteArray(rowBytes).also { file.seek(row.toLong() * rowBytes); file.readFully(it) }
                db.query("SELECT embedding FROM $table WHERE $idColumn = ?", arrayOf(ids[row])).use { c ->
                    c.moveToFirst() && c.getBlob(0).contentEquals(inFile)
                }
            }
        }

    private fun readIds(file: File): LongArray {
        val bytes = ByteBuffer.wrap(file.readBytes()).order(ByteOrder.LITTLE_ENDIAN)
        return LongArray(bytes.remaining() / 8) { bytes.getLong() }
    }

    private fun load(db: SupportSQLiteDatabase, table: String, idColumn: String, size: Int, stamp: Long): Loaded {
        val rows = db.query("SELECT COUNT(*) FROM $table").use { it.moveToFirst(); it.getInt(0) } // once per load, not per search
        val ids = LongArray(rows)
        val held = if (mode.mapped) VectorMode.HEAP_F32 else mode // a mapped mode on an in-memory database
        val block = if (held == VectorMode.HEAP_F32) null else VectorBlock(held, rows, size, null)
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
        return Loaded(stamp, mode, ids, matrix, block, size)
    }

    internal fun toBlob(vector: FloatArray): ByteArray =
        ByteBuffer.allocate(vector.size * 4).order(ByteOrder.LITTLE_ENDIAN).apply { asFloatBuffer().put(vector) }.array()

    internal fun fromBlob(bytes: ByteArray): FloatArray =
        FloatArray(bytes.size / 4).also { ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(it) }
}
