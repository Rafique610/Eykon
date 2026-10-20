package com.eykon.memory.video

import android.content.Context
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.eykon.memory.ml.vision.ImageEmbedder
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Card EYKO-16: a job that gets through every stage leaves its video ready to search; one that
 * fails leaves it failed with the reason, and Retry starts it again at the stage that failed.
 * Stand-in stages are used so a failure can be switched on and off.
 */
@RunWith(AndroidJUnit4::class)
class VideoFinishTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var jobs: VideoJobs
    private lateinit var repository: VideoRepository
    private val ran = ArrayList<String>()
    private var breakSecondStage = false

    private val stages: List<Pair<String, Stage>> = listOf(
        "first" to { _, _ -> ran.add("first"); Unit },
        "second" to { _, _ -> ran.add("second"); if (breakSecondStage) throw IllegalStateException("the sound file is missing") },
        "finish" to VideoFinish::run,
    )

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        helper = FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build())
        db = helper.writableDatabase
        jobs = VideoJobs { db }
        repository = VideoRepository { db }
        VideoVectors.clearCache()
    }

    @After
    fun close() {
        helper.close()
        VideoVectors.clearCache()
    }

    private fun add(videoId: String, createdAt: String = "2026-10-07T18:42:00Z") {
        repository.insert(Video(videoId = videoId, filePath = File(context.cacheDir, "$videoId/$videoId.mp4").absolutePath, recordedAt = createdAt, createdAt = createdAt, durationS = 10.0))
        jobs.enqueue(videoId)
    }

    private fun work() = VideoWorker({ db }, jobs, stages).drain()

    private fun row(videoId: String) = repository.listWithJobs().single { it.video.videoId == videoId }

    @Test
    fun aJobThatGetsThroughEveryStageLeavesItsVideoReadyAndItsJobDone() {
        add("clip")
        assertEquals("processing", row("clip").video.status)
        work()

        val after = row("clip")
        assertEquals(listOf("ready", "done", "finish"), listOf(after.video.status, after.jobStatus, after.jobStage))
        assertEquals(listOf("first", "second"), ran)
    }

    @Test
    fun finishDeletesTheFilesOfDroppedFramesAndKeepsTheKeptOnes() {
        add("clip")
        val videosDir = File(context.cacheDir, "videos-finish").apply { deleteRecursively(); mkdirs() }
        db.execSQL("UPDATE videos SET file_path = ? WHERE video_id = 'clip'", arrayOf(File(videosDir, "clip/clip.mp4").absolutePath))
        val files = (1..3).map { File(videosDir, "clip/frames/%06d.jpg".format(it)).apply { parentFile!!.mkdirs(); writeText("x") } }
        files.forEachIndexed { i, _ ->
            db.execSQL(
                "INSERT INTO frames (video_id, frame_no, t_s, path, kept, drop_reason) VALUES ('clip', ?, ?, ?, ?, ?)",
                arrayOf(i + 1, i / 3.0, "clip/frames/%06d.jpg".format(i + 1), if (i == 1) 1 else 0, if (i == 1) null else "less sharp"),
            )
        }
        work()

        assertEquals(listOf(false, true, false), files.map { it.exists() })
        assertEquals(3L, db.query("SELECT COUNT(*) FROM frames WHERE video_id = 'clip'").use { it.moveToFirst(); it.getLong(0) }) // rows stay
    }

    @Test
    fun aJobThatKeepsFailingLeavesItsVideoFailedWithTheStageReachedAndTheReason() {
        breakSecondStage = true
        add("clip")
        work()

        val after = row("clip")
        assertEquals(listOf("failed", "failed", "first"), listOf(after.video.status, after.jobStatus, after.jobStage)) // "first" is the last stage that finished
        assertEquals(VideoWorker.RETRIES, after.jobAttempts)
        assertEquals("IllegalStateException: the sound file is missing", after.jobError)
    }

    @Test
    fun retryStartsAgainAtTheStageThatFailedAndFinishesOnceTheCauseIsGone() {
        breakSecondStage = true
        add("clip")
        work()
        ran.clear()
        breakSecondStage = false // the cause is fixed

        jobs.retry(row("clip").jobId!!)
        val waiting = row("clip")
        assertEquals(listOf("processing", "queued", "first"), listOf(waiting.video.status, waiting.jobStatus, waiting.jobStage))
        assertEquals(0, waiting.jobAttempts)
        assertEquals(null, waiting.jobError)
        work()

        val after = row("clip")
        assertEquals(listOf("ready", "done", "finish"), listOf(after.video.status, after.jobStatus, after.jobStage))
        assertEquals(listOf("second"), ran) // the stage that had already finished did not run again
    }

    @Test
    fun retryDoesNothingToAJobThatDidNotFail() {
        add("clip")
        work()
        jobs.retry(row("clip").jobId!!)
        assertEquals(listOf("ready", "done"), listOf(row("clip").video.status, row("clip").jobStatus))
    }

    @Test
    fun theListShowsRealCountsForEachVideo() {
        add("clip")
        db.execSQL("INSERT INTO frames (video_id, frame_no, t_s, path, kept) VALUES ('clip', 1, 0.0, 'a.jpg', 1), ('clip', 2, 0.3, 'b.jpg', 0), ('clip', 3, 0.7, 'c.jpg', 1)")
        db.execSQL("INSERT INTO audio_segments (video_id, start_s, end_s, is_speech, loudness_db) VALUES ('clip', 0, 2, 1, -20), ('clip', 2, 4, 0, -50)")
        db.execSQL("INSERT INTO transcript_chunks (video_id, start_s, end_s, text) VALUES ('clip', 0, 2, 'hello'), ('clip', 2, 4, 'again'), ('clip', 4, 6, 'bye')")
        add("other", createdAt = "2026-10-08T09:00:00Z")

        val clip = row("clip")
        assertEquals(listOf(2, 1, 3), listOf(clip.keptFrames, clip.speechSegments, clip.transcriptChunks))
        assertEquals(listOf(0, 0, 0), row("other").let { listOf(it.keptFrames, it.speechSegments, it.transcriptChunks) })
        assertEquals(listOf("other", "clip"), repository.listWithJobs().map { it.video.videoId }) // newest first
        assertEquals(listOf("other"), repository.listWithJobs(limit = 1).map { it.video.videoId })
    }

    @Test
    fun onlyReadyVideosAreSearched() {
        fun along(direction: Int) = FloatArray(ImageEmbedder.DIMENSIONS).also { it[direction] = 1f }
        for ((n, id) in listOf("done", "busy", "broken").withIndex()) {
            add(id)
            db.execSQL("INSERT INTO frames (video_id, frame_no, t_s, path) VALUES (?, 1, 0.0, ?)", arrayOf(id, "$id/frames/000001.jpg"))
            VideoVectors.put(db, "image_vec", db.query("SELECT last_insert_rowid()").use { it.moveToFirst(); it.getLong(0) }, along(n))
        }
        db.execSQL("UPDATE videos SET status = 'ready' WHERE video_id = 'done'")
        db.execSQL("UPDATE videos SET status = 'failed' WHERE video_id = 'broken'")

        // a phrase that matches the unfinished video best still only returns the ready one
        val hits = VideoSearch.frames(db, "anything", 20) { along(1) }
        assertEquals(listOf("done"), hits.map { it.videoId })
        assertTrue(hits.single().score == 0f)
    }

    @Test
    fun aVideoWhoseJobIsPutBackBecauseNewStagesExistIsNotReadyUntilItFinishesThem() {
        add("clip")
        VideoWorker({ db }, jobs, stages.take(1) + stages.takeLast(1)).drain() // an older pipeline: first, finish
        assertEquals("ready", row("clip").video.status)

        jobs.requeueBehind("newer-last-stage")
        assertEquals(listOf("processing", "queued"), listOf(row("clip").video.status, row("clip").jobStatus))
    }
}
