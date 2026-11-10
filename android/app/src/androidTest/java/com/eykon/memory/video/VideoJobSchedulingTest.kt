package com.eykon.memory.video

import android.content.Context
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.work.Configuration
import androidx.work.WorkManager
import androidx.work.testing.WorkManagerTestInitHelper
import kotlinx.coroutines.CancellationException
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executor
import java.util.concurrent.TimeUnit

/**
 * EYKO-44: the unique work is enqueued once, and a stopped worker does not burn the job's attempts. Run on the phone with
 * `adb shell am instrument -w -e class com.eykon.memory.video.VideoJobSchedulingTest ...` (never connectedDebugAndroidTest).
 */
@RunWith(AndroidJUnit4::class)
class VideoJobSchedulingTest {

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

    private fun queue(videoId: String = "v1"): Long {
        repository.transaction {
            repository.insert(Video(videoId = videoId, filePath = "/$videoId.mp4", recordedAt = "2026-11-10T10:00:00Z", createdAt = "2026-11-10T10:00:00Z"))
            jobs.enqueue(videoId)
        }
        return db.query("SELECT id FROM jobs WHERE video_id = ?", arrayOf(videoId)).use { it.moveToFirst(); it.getLong(0) }
    }

    private fun worker(vararg stages: Pair<String, Stage>) = VideoWorker({ db }, jobs, stages.toList(), retries = 3)

    @Test
    fun askingTwiceEnqueuesTheUniqueWorkOnce() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        // an executor that never runs anything: only the enqueueing is under test, not the real worker
        WorkManagerTestInitHelper.initializeTestWorkManager(context, Configuration.Builder().setExecutor(Executor { }).build())
        val manager = WorkManager.getInstance(context)

        VideoJobScheduler.enqueue(manager)
        VideoJobScheduler.enqueue(manager)

        val infos = manager.getWorkInfosForUniqueWork(VideoJobWorker.UNIQUE_NAME).get(5, TimeUnit.SECONDS)
        assertEquals(1, infos.size)
    }

    @Test
    fun aStoppedWorkerDoesNotCostTheJobAnAttempt() {
        val id = queue()
        val stopped: Stage = { _, _ -> throw CancellationException("worker stopped") }
        try {
            worker("one" to stopped).runOnce()
        } catch (expected: CancellationException) {
            // being stopped reaches the caller; it is not recorded as a failure
        }
        val job = jobs.get(id)!!
        assertEquals("running", job.status)
        assertEquals(0, job.attempts)

        // the next start requeues it and it finishes
        assertTrue(worker("one" to { _, _ -> }).drainWhenIdle())
        assertEquals("done", jobs.get(id)!!.status)
    }

    @Test
    fun onlyOneLoopRunsAtATime() {
        queue()
        val inside = CountDownLatch(1)
        val release = CountDownLatch(1)
        val w = worker("one" to { _, _ ->
            inside.countDown()
            release.await(10, TimeUnit.SECONDS)
        })
        val first = Thread { w.drainWhenIdle() }
        first.start()
        assertTrue(inside.await(5, TimeUnit.SECONDS))
        assertEquals("one", w.current?.second) // the notification can show the stage being worked on
        assertFalse(w.drainWhenIdle()) // a second loop (a restarted worker) must not requeue the job that is running
        release.countDown()
        first.join(10_000)
    }
}
