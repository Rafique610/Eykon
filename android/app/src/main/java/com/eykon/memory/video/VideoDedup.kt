package com.eykon.memory.video

import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.vision.ImageEmbedder
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.File

/**
 * Stage "dedup" (card EYKO-6): among the frames the filters kept, drop near-duplicates.
 * Unlike the "still" check, which only looks at the frame before, this compares each frame
 * with every unique frame so far, so a scene the camera returns to is not stored twice.
 *
 * Two layers, cheap one first:
 *  1. perceptual hash: frames whose 64-bit hashes differ in at most [HASH_MAX] bits look the same;
 *  2. image embedding (MobileCLIP): frames whose vectors have cosine >= [COSINE_MIN] show the same thing.
 * Only frames that pass layer 1 are embedded, so the model runs as rarely as possible.
 */
object VideoDedup {

    const val HASH_MAX = 6
    const val COSINE_MIN = 0.95f
    const val VECTORS_FILE = "clip_vectors.bin"
    private const val TAG = "EykonVideo"

    private class Unique(val frameId: Long, val frameNo: Int, val hash: Long, val vector: FloatArray)

    fun run(db: SupportSQLiteDatabase, videoId: String) =
        run(db, videoId) { file -> ImageEmbedder.embed(MemoryApp.instance, file) }

    /** [embed] turns a frame file into a vector of length 1; tests pass their own. */
    fun run(db: SupportSQLiteDatabase, videoId: String, embed: (File) -> FloatArray) {
        val videoFolder = db.query("SELECT file_path FROM videos WHERE video_id = ?", arrayOf(videoId)).use { cursor ->
            if (!cursor.moveToFirst()) throw IllegalStateException("video $videoId is not in the database")
            File(cursor.getString(0)).parentFile ?: throw IllegalStateException("video file has no folder")
        }
        val videosDir = videoFolder.parentFile ?: throw IllegalStateException("video folder has no parent")
        // Idempotent: frames an earlier run of this stage dropped come back before deciding again.
        db.execSQL("UPDATE frames SET kept = 1, drop_reason = NULL WHERE video_id = ? AND drop_reason LIKE 'duplicate%'", arrayOf(videoId))
        val frames = db.query("SELECT id, frame_no, path FROM frames WHERE video_id = ? AND kept = 1 ORDER BY frame_no", arrayOf(videoId)).use { cursor ->
            buildList { while (cursor.moveToNext()) add(Triple(cursor.getLong(0), cursor.getInt(1), cursor.getString(2))) }
        }

        val unique = ArrayList<Unique>()
        val hashes = ArrayList<Pair<Long, Long>>(frames.size) // frame id and hash
        val duplicates = ArrayList<Pair<Long, Int>>() // frame id and the frame number it repeats
        var byHash = 0
        var embedded = 0
        var embedNs = 0L
        val start = System.nanoTime()
        for ((id, frameNo, path) in frames) {
            val file = File(videosDir, path)
            val hash = FrameHash.dHash(VideoFilter.loadSmallGray(file))
            hashes.add(id to hash)
            val sameLook = unique.minByOrNull { FrameHash.distance(it.hash, hash) }
            if (sameLook != null && FrameHash.distance(sameLook.hash, hash) <= HASH_MAX) {
                duplicates.add(id to sameLook.frameNo)
                byHash++
                continue
            }
            val embedStart = System.nanoTime()
            val vector = embed(file)
            embedNs += System.nanoTime() - embedStart
            embedded++
            val sameThing = unique.maxByOrNull { cosine(it.vector, vector) }
            if (sameThing != null && cosine(sameThing.vector, vector) >= COSINE_MIN) {
                duplicates.add(id to sameThing.frameNo)
            } else {
                unique.add(Unique(id, frameNo, hash, vector))
            }
        }
        val ms = (System.nanoTime() - start) / 1_000_000

        // The unique frames' vectors are kept so the embedding stage (card EYKO-11) does not compute them again.
        writeVectors(File(videoFolder, VECTORS_FILE), unique.map { it.frameId to it.vector })

        db.beginTransaction()
        try {
            hashes.forEach { (id, hash) -> db.execSQL("UPDATE frames SET phash = ? WHERE id = ?", arrayOf(FrameHash.toHex(hash), id)) }
            duplicates.forEach { (id, of) ->
                db.execSQL("UPDATE frames SET kept = 0, drop_reason = ? WHERE id = ?", arrayOf("duplicate of frame $of", id))
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        val runtime = Runtime.getRuntime()
        Log.i(
            TAG,
            "dedup $videoId: kept ${unique.size} of ${frames.size} (hash dropped $byHash, embedding dropped ${duplicates.size - byHash}) in $ms ms; " +
                "embedded $embedded frames, ${if (embedded > 0) embedNs / 1_000_000 / embedded else 0} ms each; " +
                "memory java ${(runtime.totalMemory() - runtime.freeMemory()) / 1_000_000} MB, native ${android.os.Debug.getNativeHeapAllocatedSize() / 1_000_000} MB",
        )
    }

    /** Both vectors have length 1, so the dot product is the cosine. */
    private fun cosine(a: FloatArray, b: FloatArray): Float {
        var sum = 0f
        for (i in a.indices) sum += a[i] * b[i]
        return sum
    }

    private fun writeVectors(file: File, vectors: List<Pair<Long, FloatArray>>) {
        DataOutputStream(file.outputStream().buffered()).use { out ->
            out.writeInt(vectors.size)
            out.writeInt(vectors.firstOrNull()?.second?.size ?: 0)
            for ((frameId, vector) in vectors) {
                out.writeLong(frameId)
                vector.forEach(out::writeFloat)
            }
        }
    }

    /** Frame id to vector, as written by this stage. */
    fun readVectors(file: File): Map<Long, FloatArray> {
        if (!file.exists()) return emptyMap()
        DataInputStream(file.inputStream().buffered()).use { input ->
            val count = input.readInt()
            val size = input.readInt()
            return buildMap { repeat(count) { put(input.readLong(), FloatArray(size) { input.readFloat() }) } }
        }
    }
}
