package com.eykon.memory.video

import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import java.time.Instant
import kotlin.math.roundToLong

/**
 * Stage "link" (card EYKO-14): a check, not a repair. It proves that everything stored for a
 * video hangs together, so any answer can point at a real video, a real moment and a real
 * picture. If something is missing the stage fails and the job shows the reasons; it never
 * fixes data on the quiet.
 */
object VideoLink {

    private const val TAG = "EykonVideo"

    /** What must be zero for a video, each with the query that counts it. One `?` per query: the video id. */
    private val RULES = listOf(
        "kept frames without a picture hash" to
            "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND f.phash IS NULL",
        "kept frames without a scene record" to
            "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND NOT EXISTS (SELECT 1 FROM scene_records s WHERE s.frame_id = f.id)",
        "kept frames without an image vector" to
            "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND NOT EXISTS (SELECT 1 FROM image_vec v WHERE v.frame_id = f.id)",
        "texts without a text vector" to
            "SELECT COUNT(*) FROM video_texts t WHERE t.video_id = ? AND NOT EXISTS (SELECT 1 FROM text_vec v WHERE v.text_id = t.id)",
        "sound windows without a sound vector" to
            "SELECT COUNT(*) FROM audio_windows w WHERE w.video_id = ? AND NOT EXISTS (SELECT 1 FROM audio_vec v WHERE v.window_id = w.id)",
        "frames timed outside the video" to
            "SELECT COUNT(*) FROM frames f JOIN videos v ON v.video_id = f.video_id WHERE f.video_id = ? AND (f.t_s < 0 OR f.t_s > v.duration_s + 1)",
        "texts timed outside the video" to
            "SELECT COUNT(*) FROM video_texts t JOIN videos v ON v.video_id = t.video_id WHERE t.video_id = ? AND (t.start_s < 0 OR t.end_s < t.start_s OR t.end_s > v.duration_s + 1)",
        "sound segments timed outside the video" to
            "SELECT COUNT(*) FROM audio_segments a JOIN videos v ON v.video_id = a.video_id WHERE a.video_id = ? AND (a.start_s < 0 OR a.end_s < a.start_s OR a.end_s > v.duration_s + 1)",
        "transcript chunks timed outside the video" to
            "SELECT COUNT(*) FROM transcript_chunks c JOIN videos v ON v.video_id = c.video_id WHERE c.video_id = ? AND (c.start_s < 0 OR c.end_s < c.start_s OR c.end_s > v.duration_s + 1)",
        "sound windows timed outside the video" to
            "SELECT COUNT(*) FROM audio_windows w JOIN videos v ON v.video_id = w.video_id WHERE w.video_id = ? AND (w.start_s < 0 OR w.end_s < w.start_s OR w.end_s > v.duration_s + 1)",
    )

    /** Plain messages with counts, for example "1 kept frames without an image vector". Empty when all is well. */
    fun problems(db: SupportSQLiteDatabase, videoId: String): List<String> {
        val recordedAt = db.query("SELECT recorded_at FROM videos WHERE video_id = ?", arrayOf(videoId)).use { c ->
            if (c.moveToFirst()) c.getString(0) else return listOf("the video is not in the database")
        }
        val found = ArrayList<String>()
        if (runCatching { Instant.parse(recordedAt) }.isFailure) found.add("the video has no usable recording time (\"$recordedAt\")")
        for ((label, sql) in RULES) {
            val count = db.query(sql, arrayOf(videoId)).use { it.moveToFirst(); it.getInt(0) }
            if (count > 0) found.add("$count $label")
        }
        return found
    }

    fun run(db: SupportSQLiteDatabase, videoId: String) {
        val found = problems(db, videoId)
        if (found.isNotEmpty()) throw IllegalStateException(found.joinToString("; "))
        Log.i(TAG, "link $videoId: every row points at its video and moment")
    }

    /** The real clock time of a point [tS] seconds into a video recorded at [recordedAt] (ISO time, UTC). */
    fun moment(recordedAt: String, tS: Double): Instant = Instant.parse(recordedAt).plusMillis((tS * 1000).roundToLong())
}
