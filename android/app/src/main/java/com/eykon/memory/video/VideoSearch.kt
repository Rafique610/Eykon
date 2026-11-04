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

    fun frames(db: SupportSQLiteDatabase, text: String, k: Int = POOL): List<FrameHit> =
        frames(db, text, k) { TextEmbedder.embed(MemoryApp.instance, it) }

    /**
     * [embed] turns the phrase into a vector of length 1; tests pass their own.
     * EYKO-102: same hits as before, faster. Scores come as plain arrays (no boxed map), frames are
     * read as id + video + time only, one sort of packed numbers ranks them, and the path and caption
     * are read for the hits alone. Measured before and after on two phones (Head 2 document).
     */
    fun frames(db: SupportSQLiteDatabase, text: String, k: Int, embed: (String) -> FloatArray): List<FrameHit> {
        if (text.isBlank()) return emptyList()
        val all = VideoVectors.scores(db, "image_vec", embed(text))
        if (all.ids.isEmpty()) return emptyList()

        // Ready videos: where their frames live and when they were recorded.
        val videos = HashMap<String, Pair<File, String>>()
        db.query("SELECT video_id, file_path, recorded_at FROM videos WHERE status = 'ready'").use { c ->
            while (c.moveToNext()) {
                // frames.path is relative to the folder that holds every video's own folder
                val videosDir = File(c.getString(1)).parentFile?.parentFile ?: continue
                videos[c.getString(0)] = videosDir to c.getString(2)
            }
        }

        // Every kept frame of the ready videos that has a vector, in time order per video, so windows can grow over neighbours.
        val ids = LongArrayList()
        val times = DoubleArrayList()
        val scores = FloatArrayList()
        val videoOf = ArrayList<String>() // one entry per video run
        val runStart = IntArrayList()
        db.query(
            "SELECT f.id, f.video_id, f.t_s FROM frames f JOIN videos v ON v.video_id = f.video_id " +
                "WHERE v.status = 'ready' AND f.kept = 1 ORDER BY f.video_id, f.t_s",
        ).use { c ->
            while (c.moveToNext()) {
                val at = all.ids.binarySearch(c.getLong(0))
                if (at < 0) continue
                val videoId = c.getString(1)
                if (videoId !in videos) continue
                if (videoOf.isEmpty() || videoOf.last() != videoId) { videoOf.add(videoId); runStart.add(ids.size) }
                ids.add(c.getLong(0)); times.add(c.getDouble(2)); scores.add(all.scores[at])
            }
        }
        runStart.add(ids.size)
        val runOf = IntArray(ids.size).also { r -> for (v in 0 until videoOf.size) for (i in runStart[v] until runStart[v + 1]) r[i] = v }

        val windows = HashMap<Int, MutableList<Pair<Double, Double>>>()
        val hits = ArrayList<FrameHit>()
        for (row in VideoVectors.rankDescending(scores.toArray())) {
            val v = runOf[row]
            val tS = times[row]
            val taken = windows.getOrPut(v) { mutableListOf() }
            if (taken.any { (a, b) -> tS in a..b }) continue
            val from = runStart[v]
            val to = runStart[v + 1]
            val (start, end) = SearchWindows.grow(times.slice(from, to), scores.slice(from, to), row - from)
            taken.add(start to end)
            hits.add(hit(db, ids[row], videoOf[v], videos.getValue(videoOf[v]), tS, scores[row], start, end))
            if (hits.size == k) break
        }
        return hits
    }

    /** Path and caption are read only for a hit. */
    private fun hit(db: SupportSQLiteDatabase, id: Long, videoId: String, video: Pair<File, String>, tS: Double, score: Float, start: Double, end: Double): FrameHit =
        db.query("SELECT f.path, s.caption FROM frames f LEFT JOIN scene_records s ON s.frame_id = f.id WHERE f.id = ?", arrayOf(id)).use { c ->
            c.moveToFirst()
            FrameHit(id, videoId, video.second, tS, File(video.first, c.getString(0)), score, if (c.isNull(1)) null else c.getString(1), start, end)
        }

    // Growable primitive arrays, so a search over many frames boxes nothing.
    private class LongArrayList { var a = LongArray(1024); var size = 0; fun add(x: Long) { if (size == a.size) a = a.copyOf(size * 2); a[size++] = x }; operator fun get(i: Int) = a[i] }
    private class DoubleArrayList { var a = DoubleArray(1024); var size = 0; fun add(x: Double) { if (size == a.size) a = a.copyOf(size * 2); a[size++] = x }; operator fun get(i: Int) = a[i]; fun slice(from: Int, to: Int) = a.copyOfRange(from, to) }
    private class FloatArrayList { var a = FloatArray(1024); var size = 0; fun add(x: Float) { if (size == a.size) a = a.copyOf(size * 2); a[size++] = x }; operator fun get(i: Int) = a[i]; fun slice(from: Int, to: Int) = a.copyOfRange(from, to); fun toArray() = a.copyOf(size) }
    private class IntArrayList { var a = IntArray(64); var size = 0; fun add(x: Int) { if (size == a.size) a = a.copyOf(size * 2); a[size++] = x }; operator fun get(i: Int) = a[i] }
}
