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
    /** EYKO-126: the gallery file the stages read (no copy is made); null when [filePath] holds a copy. */
    val sourceUri: String? = null,
    /** EYKO-126: the file's name in the gallery, for the screen and the notification; null for older videos. */
    val displayName: String? = null,
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
            "INSERT INTO videos (video_id, file_path, recorded_at, created_at, duration_s, lat, lon, status, content_hash, source_uri, display_name) " +
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            arrayOf(
                video.videoId, video.filePath, video.recordedAt, video.createdAt,
                video.durationS, video.lat, video.lon, video.status, video.contentHash, video.sourceUri, video.displayName,
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
                            // the video's eleven columns come first (0 to 10), then the job's
                            jobStatus = if (cursor.isNull(11)) null else cursor.getString(11),
                            jobStage = if (cursor.isNull(12)) "" else cursor.getString(12),
                            jobAttempts = if (cursor.isNull(13)) 0 else cursor.getInt(13),
                            jobError = if (cursor.isNull(14)) null else cursor.getString(14),
                            jobId = if (cursor.isNull(15)) null else cursor.getLong(15),
                            keptFrames = cursor.getInt(16),
                            speechSegments = cursor.getInt(17),
                            transcriptChunks = cursor.getInt(18),
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
        sourceUri = if (isNull(9)) null else getString(9),
        displayName = if (isNull(10)) null else getString(10),
    )

    private companion object {
        const val COLUMNS = "video_id, file_path, recorded_at, created_at, duration_s, lat, lon, status, content_hash, source_uri, display_name"
    }
}
