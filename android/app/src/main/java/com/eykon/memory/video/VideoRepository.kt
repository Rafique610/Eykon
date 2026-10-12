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
)

data class VideoWithJob(
    val video: Video,
    val jobStatus: String?,
    val jobStage: String,
    val jobAttempts: Int,
    val jobError: String?,
)

/** Plain SQL with ? parameters over the app's database, like the laptop's repository.py. */
class VideoRepository(private val db: () -> SupportSQLiteDatabase) {

    fun insert(video: Video) {
        db().execSQL(
            "INSERT INTO videos (video_id, file_path, recorded_at, created_at, duration_s, lat, lon, status) " +
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            arrayOf(
                video.videoId, video.filePath, video.recordedAt, video.createdAt,
                video.durationS, video.lat, video.lon, video.status,
            ),
        )
    }

    fun get(videoId: String): Video? =
        db().query("SELECT $COLUMNS FROM videos WHERE video_id = ?", arrayOf(videoId)).use { cursor ->
            if (cursor.moveToFirst()) cursor.toVideo() else null
        }

    fun list(): List<Video> =
        db().query("SELECT $COLUMNS FROM videos ORDER BY created_at DESC").use { cursor ->
            buildList { while (cursor.moveToNext()) add(cursor.toVideo()) }
        }

    /** Each video with its job (the newest one), for the list on screen. */
    fun listWithJobs(): List<VideoWithJob> =
        db().query(
            "SELECT ${COLUMNS.split(", ").joinToString { "v.$it" }}, j.status, j.stage, j.attempts, j.error " +
                "FROM videos v LEFT JOIN jobs j ON j.id = (SELECT MAX(id) FROM jobs WHERE video_id = v.video_id) " +
                "ORDER BY v.created_at DESC",
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        VideoWithJob(
                            video = cursor.toVideo(),
                            jobStatus = if (cursor.isNull(8)) null else cursor.getString(8),
                            jobStage = if (cursor.isNull(9)) "" else cursor.getString(9),
                            jobAttempts = if (cursor.isNull(10)) 0 else cursor.getInt(10),
                            jobError = if (cursor.isNull(11)) null else cursor.getString(11),
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
    )

    private companion object {
        const val COLUMNS = "video_id, file_path, recorded_at, created_at, duration_s, lat, lon, status"
    }
}
