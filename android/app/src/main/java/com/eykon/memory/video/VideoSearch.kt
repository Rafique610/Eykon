package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.vision.TextEmbedder
import java.io.File

/**
 * One moment a search returned. [score] is the cosine between the typed phrase and the best frame,
 * [tS] that frame's second, and [startS] to [endS] the stretch of the video the moment covers (card EYKO-58).
 */
data class FrameHit(
    val frameId: Long,
    val videoId: String,
    val recordedAt: String,
    val tS: Double,
    val file: File,
    val score: Float,
    val caption: String?,
    val startS: Double = tS,
    val endS: Double = tS,
)

/**
 * Search by typed phrase over the stored frame vectors (the core of card EYKO-19): the phrase
 * becomes a vector with MobileCLIP's text encoder and the frames whose own vectors point the
 * same way come back, best first. It does not use the captions, so it can find things the
 * detector has no name for. Each hit grows into a window over the neighbouring frames that
 * still match ([SearchWindows]); a frame inside an earlier window is not returned again.
 *
 * Only videos marked ready are searched (their processing finished without a problem).
 * Not here yet, each with its own card: date ranges and a reworded question (EYKO-18),
 * latest sighting only (EYKO-17 onward).
 */
object VideoSearch {

    /** How many hits a search returns: Phase 1's pool size. */
    const val POOL = 20

    private class Frame(val id: Long, val videoId: String, val tS: Double, val file: File, val recordedAt: String, val caption: String?)

    fun frames(db: SupportSQLiteDatabase, text: String, k: Int = POOL): List<FrameHit> =
        frames(db, text, k) { TextEmbedder.embed(MemoryApp.instance, it) }

    /** [embed] turns the phrase into a vector of length 1; tests pass their own. */
    fun frames(db: SupportSQLiteDatabase, text: String, k: Int, embed: (String) -> FloatArray): List<FrameHit> {
        if (text.isBlank()) return emptyList()
        val scores = VideoVectors.knn(db, "image_vec", embed(text), Int.MAX_VALUE).toMap()
        if (scores.isEmpty()) return emptyList()
        // Every kept frame of the ready videos, in time order per video, so windows can grow over neighbours.
        val byVideo = db.query(
            "SELECT f.id, f.video_id, f.t_s, f.path, v.recorded_at, v.file_path, s.caption FROM frames f " +
                "JOIN videos v ON v.video_id = f.video_id LEFT JOIN scene_records s ON s.frame_id = f.id " +
                "WHERE v.status = 'ready' AND f.kept = 1 ORDER BY f.video_id, f.t_s",
        ).use { c ->
            buildList {
                while (c.moveToNext()) {
                    if (c.getLong(0) !in scores) continue
                    // frames.path is relative to the folder that holds every video's own folder
                    val videosDir = File(c.getString(5)).parentFile?.parentFile ?: continue
                    add(Frame(c.getLong(0), c.getString(1), c.getDouble(2), File(videosDir, c.getString(3)), c.getString(4), if (c.isNull(6)) null else c.getString(6)))
                }
            }
        }.groupBy { it.videoId }

        val windows = HashMap<String, MutableList<Pair<Double, Double>>>()
        val hits = ArrayList<FrameHit>()
        val order = byVideo.flatMap { (v, fs) -> fs.indices.map { v to it } }.sortedByDescending { (v, i) -> scores.getValue(byVideo.getValue(v)[i].id) }
        for ((videoId, i) in order) {
            val frames = byVideo.getValue(videoId)
            val hit = frames[i]
            val taken = windows.getOrPut(videoId) { mutableListOf() }
            if (taken.any { (a, b) -> hit.tS in a..b }) continue
            val (start, end) = SearchWindows.grow(DoubleArray(frames.size) { frames[it].tS }, FloatArray(frames.size) { scores.getValue(frames[it].id) }, i)
            taken.add(start to end)
            hits.add(FrameHit(hit.id, videoId, hit.recordedAt, hit.tS, hit.file, scores.getValue(hit.id), hit.caption, start, end))
            if (hits.size == k) break
        }
        return hits
    }
}
