package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.vision.TextEmbedder
import java.io.File

/** One frame a search returned. [score] is the cosine between the typed phrase and the frame. */
data class FrameHit(
    val frameId: Long,
    val videoId: String,
    val recordedAt: String,
    val tS: Double,
    val file: File,
    val score: Float,
    val caption: String?,
)

/**
 * Search by typed phrase over the stored frame vectors (the core of card EYKO-19): the phrase
 * becomes a vector with MobileCLIP's text encoder and the frames whose own vectors point the
 * same way come back, best first. It does not use the captions, so it can find things the
 * detector has no name for.
 *
 * Only videos marked ready are searched (their processing finished without a problem).
 * Not here yet, each with its own card: date ranges and a reworded question (EYKO-18),
 * latest sighting only (EYKO-17 onward).
 */
object VideoSearch {

    /** How many hits a search returns: Phase 1's pool size. */
    const val POOL = 20

    /** How many nearest frames are looked at before the ones from videos that are not ready are left out. */
    private const val CANDIDATES = 200

    fun frames(db: SupportSQLiteDatabase, text: String, k: Int = POOL): List<FrameHit> =
        frames(db, text, k) { TextEmbedder.embed(MemoryApp.instance, it) }

    /** [embed] turns the phrase into a vector of length 1; tests pass their own. */
    fun frames(db: SupportSQLiteDatabase, text: String, k: Int, embed: (String) -> FloatArray): List<FrameHit> {
        if (text.isBlank()) return emptyList()
        return VideoVectors.knn(db, "image_vec", embed(text), maxOf(k, CANDIDATES)).mapNotNull { (frameId, score) ->
            db.query(
                "SELECT f.video_id, v.recorded_at, f.t_s, f.path, v.file_path, s.caption FROM frames f " +
                    "JOIN videos v ON v.video_id = f.video_id LEFT JOIN scene_records s ON s.frame_id = f.id WHERE f.id = ? AND v.status = 'ready'",
                arrayOf(frameId),
            ).use { c ->
                if (!c.moveToFirst()) return@use null
                // frames.path is relative to the folder that holds every video's own folder
                val videosDir = File(c.getString(4)).parentFile?.parentFile ?: return@use null
                FrameHit(frameId, c.getString(0), c.getString(1), c.getDouble(2), File(videosDir, c.getString(3)), score, if (c.isNull(5)) null else c.getString(5))
            }
        }.take(k)
    }
}
