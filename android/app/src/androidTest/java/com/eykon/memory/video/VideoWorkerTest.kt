package com.eykon.memory.video

import android.content.Context
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** The job queue and worker on the phone's own SQLite, with stages made up in each test. */
@RunWith(AndroidJUnit4::class)
class VideoWorkerTest {

    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var jobs: VideoJobs
    private lateinit var repository: VideoRepository

    @Before
    fun open() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        helper = FrameworkSQLiteOpenHelperFactory().create(
            SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build(),
        )
        db = helper.writableDatabase
        jobs = VideoJobs { db }
        repository = VideoRepository { db }
    }

    @After
    fun close() = helper.close()

    /** A video with one queued job; returns the job id. */
    private fun queue(videoId: String = "v1"): Long {
        repository.transaction {
            repository.insert(
                Video(videoId = videoId, filePath = "/$videoId.mp4", recordedAt = "2026-10-12T16:00:00Z", createdAt = "2026-10-12T16:00:00Z"),
            )
            jobs.enqueue(videoId)
        }
        return db.query("SELECT id FROM jobs WHERE video_id = ?", arrayOf(videoId)).use { it.moveToFirst(); it.getLong(0) }
    }

    /** A stage that writes one frames row the idempotent way: delete its rows first, then insert. */
    private fun frameStage(frameNo: Int): Stage = { database, videoId ->
        database.execSQL("DELETE FROM frames WHERE video_id = ? AND frame_no = ?", arrayOf(videoId, frameNo))
        database.execSQL("INSERT INTO frames (video_id, frame_no, t_s, path) VALUES (?, ?, 0, 'x.jpg')", arrayOf(videoId, frameNo))
    }

    private fun frames(): Long = db.query("SELECT COUNT(*) FROM frames").use { it.moveToFirst(); it.getLong(0) }

    private fun worker(vararg stages: Pair<String, Stage>) = VideoWorker({ db }, jobs, stages.toList(), retries = 3)

    @Test
    fun aJobWithTwoStagesFinishesAsDone() {
        val id = queue()
        worker("one" to frameStage(1), "two" to frameStage(2)).drain()

        val job = jobs.get(id)!!
        assertEquals("done", job.status)
        assertEquals("two", job.stage)
        assertEquals(0, job.attempts)
        assertEquals(2L, frames())
    }

    @Test
    fun aJobWithNoStagesIsDoneAtOnce() {
        val id = queue()
        assertTrue(worker().runOnce())
        assertEquals("done", jobs.get(id)!!.status)
        assertFalse(worker().runOnce()) // the queue is empty now
    }

    @Test
    fun aStageThatFailsTwiceThenWorksEndsDoneWithTwoAttempts() {
        val id = queue()
        var calls = 0
        val flaky: Stage = { _, _ -> if (++calls <= 2) throw IllegalStateException("not yet") }
        worker("one" to frameStage(1), "flaky" to flaky).drain()

        val job = jobs.get(id)!!
        assertEquals("done", job.status)
        assertEquals(2, job.attempts)
        assertEquals(3, calls)
        assertEquals(1L, frames()) // stage "one" ran once and was not repeated on the retries
    }

    @Test
    fun aStageThatAlwaysFailsEndsFailedWithAShortError() {
        val id = queue()
        var calls = 0
        val broken: Stage = { _, _ -> calls++; throw IllegalArgumentException("bad file " + "x".repeat(500)) }
        worker("broken" to broken).drain()

        val job = jobs.get(id)!!
        assertEquals("failed", job.status)
        assertEquals(3, job.attempts)
        assertEquals(3, calls)
        assertTrue(job.error!!.startsWith("IllegalArgumentException: bad file"))
        assertTrue(job.error!!.length < 240)
        assertFalse(job.error!!.contains("\tat ")) // no stack trace
    }

    @Test
    fun anInterruptedJobResumesAfterItsSavedStageWithNoDuplicateRows() {
        val id = queue()
        // First run, by hand: the job is taken, stage "one" finishes, then the app dies.
        // Nothing more happens: the process is gone and the job is left 'running'.
        val taken = jobs.claim()!!
        frameStage(1)(db, taken.videoId)
        jobs.stageDone(taken.id, "one")
        assertEquals("running", jobs.get(id)!!.status)

        // Next start of the app.
        jobs.requeueInterrupted()
        var oneRanAgain = false
        val one: Stage = { database, videoId -> oneRanAgain = true; frameStage(1)(database, videoId) }
        worker("one" to one, "two" to frameStage(2)).drain()

        val job = jobs.get(id)!!
        assertEquals("done", job.status)
        assertEquals("two", job.stage)
        assertFalse(oneRanAgain)
        assertEquals(2L, frames())
    }

    @Test
    fun jobsAreTakenOldestFirstAndOnlyOnce() {
        queue("a")
        queue("b")
        assertEquals("a", jobs.claim()!!.videoId)
        assertEquals("b", jobs.claim()!!.videoId)
        assertNull(jobs.claim())
    }

    @Test
    fun kickRunsQueuedJobsInTheBackground() = runBlocking {
        val id = queue()
        worker("one" to frameStage(1)).kick(CoroutineScope(Dispatchers.Default))
        withTimeout(5_000) {
            while (jobs.get(id)!!.status != "done") delay(20)
        }
        assertEquals(1L, frames())
    }

    @Test
    fun deletingAVideoDeletesItsJob() {
        val id = queue()
        db.execSQL("DELETE FROM videos WHERE video_id = 'v1'")
        assertNull(jobs.get(id))
    }
}
