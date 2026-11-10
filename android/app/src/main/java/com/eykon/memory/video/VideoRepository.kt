package com.eykon.memory.video

import android.database.Cursor
import androidx.sqlite.db.SupportSQLiteDatabase

data class Video(
    val videoId: String,
    val filePath: String,
    val recordedAt: String,
    val createdAt: String,
    val durationS: Double = 0.0,
    val lat: Double? = null,
    val lon: Double? = null,
    val status: String = "processing",
    /** SHA-256 of the copied file (EYKO-71); null for videos saved before the column existed. */
    val contentHash: String? = null,
)

/** A video with its newest job and real counts of what is stored for it. */
data class VideoWithJob(
    val video: Video,
    val jobStatus: String?,
    val jobStage: String,
    val jobAttempts: Int,
    val jobError: String?,
    val jobId: Long? = null,
    val keptFrames: Int = 0,
    val speechSegments: Int = 0,
    val transcriptChunks: Int = 0,
)

/** Plain SQL with ? parameters over the app's database, like the laptop's repository.py. */
class VideoRepository(private val db: () -> SupportSQLiteDatabase) {

    fun insert(video: Video) {
        db().execSQL(
            "INSERT INTO videos (video_id, file_path, recorded_at, created_at, duration_s, lat, lon, status, content_hash) " +
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            arrayOf(
                video.videoId, video.filePath, video.recordedAt, video.createdAt,
                video.durationS, video.lat, video.lon, video.status, video.contentHash,
            ),
        )
    }

    /** The oldest saved video with exactly these bytes, or null. */
    fun findByHash(contentHash: String): Video? =
        db().query("SELECT $COLUMNS FROM videos WHERE content_hash = ? ORDER BY created_at LIMIT 1", arrayOf(contentHash)).use { cursor ->
            if (cursor.moveToFirst()) cursor.toVideo() else null
        }

    fun get(videoId: String): Video? =
        db().query("SELECT $COLUMNS FROM videos WHERE video_id = ?", arrayOf(videoId)).use { cursor ->
            if (cursor.moveToFirst()) cursor.toVideo() else null
        }

    fun list(): List<Video> =
        db().query("SELECT $COLUMNS FROM videos ORDER BY created_at DESC").use { cursor ->
            buildList { while (cursor.moveToNext()) add(cursor.toVideo()) }
        }

    /** The newest [limit] videos, each with its job (the newest one) and counts, for the list on screen. */
    fun listWithJobs(limit: Int = 20): List<VideoWithJob> =
        db().query(
            "SELECT ${COLUMNS.split(", ").joinToString { "v.$it" }}, j.status, j.stage, j.attempts, j.error, j.id, " +
                "(SELECT COUNT(*) FROM frames f WHERE f.video_id = v.video_id AND f.kept = 1), " +
                "(SELECT COUNT(*) FROM audio_segments a WHERE a.video_id = v.video_id AND a.is_speech = 1), " +
                "(SELECT COUNT(*) FROM transcript_chunks c WHERE c.video_id = v.video_id) " +
                "FROM videos v LEFT JOIN jobs j ON j.id = (SELECT MAX(id) FROM jobs WHERE video_id = v.video_id) " +
                "ORDER BY v.created_at DESC LIMIT ?",
            arrayOf(limit),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        VideoWithJob(
                            video = cursor.toVideo(),
                            // the video's nine columns come first (0 to 8), then the job's
                            jobStatus = if (cursor.isNull(9)) null else cursor.getString(9),
                            jobStage = if (cursor.isNull(10)) "" else cursor.getString(10),
                            jobAttempts = if (cursor.isNull(11)) 0 else cursor.getInt(11),
                            jobError = if (cursor.isNull(12)) null else cursor.getString(12),
                            jobId = if (cursor.isNull(13)) null else cursor.getLong(13),
                            keptFrames = cursor.getInt(14),
                            speechSegments = cursor.getInt(15),
                            transcriptChunks = cursor.getInt(16),
                        ),
                    )
                }
            }
        }

    /** Run several writes as one: all of them happen, or none. */
    fun <T> transaction(block: () -> T): T {
        val database = db()
        database.beginTransaction()
        try {
            return block().also { database.setTransactionSuccessful() }
        } finally {
            database.endTransaction()
        }
    }

    private fun Cursor.toVideo() = Video(
        videoId = getString(0),
        filePath = getString(1),
        recordedAt = getString(2),
        createdAt = getString(3),
        durationS = getDouble(4),
        lat = if (isNull(5)) null else getDouble(5),
        lon = if (isNull(6)) null else getDouble(6),
        status = getString(7),
        contentHash = if (isNull(8)) null else getString(8),
    )

    private companion object {
        const val COLUMNS = "video_id, file_path, recorded_at, created_at, duration_s, lat, lon, status, content_hash"
    }
}
