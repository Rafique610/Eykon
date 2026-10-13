package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase
import java.time.Instant

data class Job(
    val id: Long,
    val videoId: String,
    val status: String,
    val stage: String,
    val attempts: Int,
    val error: String?,
)

/** The job queue. SQLite is the queue: no other service is involved. */
class VideoJobs(private val db: () -> SupportSQLiteDatabase) {

    private fun now() = Instant.now().toString()

    /** The caller runs this in the same transaction as the videos insert. */
    fun enqueue(videoId: String) {
        val now = now()
        db().execSQL("INSERT INTO jobs (video_id, created_at, updated_at) VALUES (?, ?, ?)", arrayOf(videoId, now, now))
    }

    /** Take the oldest queued job. The transaction stops two workers taking the same job. */
    fun claim(): Job? {
        val database = db()
        database.beginTransaction()
        try {
            val job = database.query("SELECT $COLUMNS FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1").use { cursor ->
                if (cursor.moveToFirst()) Job(cursor.getLong(0), cursor.getString(1), "running", cursor.getString(3), cursor.getInt(4), null) else null
            }
            if (job != null) {
                database.execSQL("UPDATE jobs SET status = 'running', updated_at = ? WHERE id = ?", arrayOf(now(), job.id))
            }
            database.setTransactionSuccessful()
            return job
        } finally {
            database.endTransaction()
        }
    }

    fun stageDone(jobId: Long, stage: String) =
        db().execSQL("UPDATE jobs SET stage = ?, updated_at = ? WHERE id = ?", arrayOf(stage, now(), jobId))

    fun done(jobId: Long) =
        db().execSQL("UPDATE jobs SET status = 'done', error = NULL, updated_at = ? WHERE id = ?", arrayOf(now(), jobId))

    /** One more failed attempt: back to the queue, or failed for good once the retries are used up. */
    fun attemptFailed(job: Job, error: String, retries: Int) {
        val attempts = job.attempts + 1
        val status = if (attempts >= retries) "failed" else "queued"
        db().execSQL(
            "UPDATE jobs SET status = ?, attempts = ?, error = ?, updated_at = ? WHERE id = ?",
            arrayOf(status, attempts, error, now(), job.id),
        )
    }

    /** A job still 'running' when the app starts was interrupted; put it back in the queue. */
    fun requeueInterrupted() =
        db().execSQL("UPDATE jobs SET status = 'queued', updated_at = ? WHERE status = 'running'", arrayOf(now()))

    /**
     * A job that finished before the pipeline grew stopped at an earlier stage than today's
     * last one. Back in the queue, it runs only the stages it has not done yet.
     */
    fun requeueBehind(lastStage: String) =
        db().execSQL("UPDATE jobs SET status = 'queued', updated_at = ? WHERE status = 'done' AND stage != ?", arrayOf(now(), lastStage))

    fun hasQueued(): Boolean =
        db().query("SELECT 1 FROM jobs WHERE status = 'queued' LIMIT 1").use { it.moveToFirst() }

    fun get(jobId: Long): Job? =
        db().query("SELECT $COLUMNS FROM jobs WHERE id = ?", arrayOf(jobId)).use { cursor ->
            if (cursor.moveToFirst()) {
                Job(cursor.getLong(0), cursor.getString(1), cursor.getString(2), cursor.getString(3), cursor.getInt(4), if (cursor.isNull(5)) null else cursor.getString(5))
            } else null
        }

    private companion object {
        const val COLUMNS = "id, video_id, status, stage, attempts, error"
    }
}
