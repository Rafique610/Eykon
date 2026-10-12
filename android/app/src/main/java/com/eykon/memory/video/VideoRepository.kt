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
