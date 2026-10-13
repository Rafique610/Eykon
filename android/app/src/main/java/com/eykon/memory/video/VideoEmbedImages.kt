package com.eykon.memory.video

import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.vision.ImageEmbedder
import java.io.File

/**
 * Stage "embed_images" (card EYKO-11): one MobileCLIP vector in image_vec for every frame that
 * is still kept, so frames can be searched. The dedup stage already made these vectors and
 * saved them next to the video; only a frame without a saved vector is embedded here.
 */
object VideoEmbedImages {

    private const val TAG = "EykonVideo"

    fun run(db: SupportSQLiteDatabase, videoId: String) =
        run(db, videoId) { file -> ImageEmbedder.embed(MemoryApp.instance, file) }

    /** [embed] turns a frame file into a vector of length 1; tests pass their own. */
    fun run(db: SupportSQLiteDatabase, videoId: String, embed: (File) -> FloatArray) {
        val videoFolder = db.query("SELECT file_path FROM videos WHERE video_id = ?", arrayOf(videoId)).use { cursor ->
            if (!cursor.moveToFirst()) throw IllegalStateException("video $videoId is not in the database")
            File(cursor.getString(0)).parentFile ?: throw IllegalStateException("video file has no folder")
        }
        val videosDir = videoFolder.parentFile ?: throw IllegalStateException("video folder has no parent")
        val kept = db.query("SELECT id, path FROM frames WHERE video_id = ? AND kept = 1 ORDER BY t_s", arrayOf(videoId)).use { cursor ->
            buildList { while (cursor.moveToNext()) add(cursor.getLong(0) to cursor.getString(1)) }
        }
        val saved = VideoDedup.readVectors(File(videoFolder, VideoDedup.VECTORS_FILE))
        val start = System.nanoTime()
        var computed = 0
        val vectors = kept.map { (id, path) -> id to (saved[id] ?: embed(File(videosDir, path)).also { computed++ }) }

        db.beginTransaction()
        try {
            // Idempotent: this video's vectors from an earlier run go first.
            db.execSQL("DELETE FROM image_vec WHERE frame_id IN (SELECT id FROM frames WHERE video_id = ?)", arrayOf(videoId))
            vectors.forEach { (id, vector) -> VideoVectors.put(db, "image_vec", id, vector) }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        VideoVectors.clearCache("image_vec")
        Log.i(TAG, "embed_images $videoId: ${vectors.size} vectors stored (${vectors.size - computed} reused, $computed computed) in ${(System.nanoTime() - start) / 1_000_000} ms")
    }
}
