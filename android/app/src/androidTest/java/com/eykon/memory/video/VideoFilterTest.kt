package com.eykon.memory.video

import android.content.Context
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * The filter stage on a real phone. test_clip_still.mp4 is 5 s of one unchanging picture;
 * test_clip.mp4 is 10 s of a moving test pattern.
 */
@RunWith(AndroidJUnit4::class)
class VideoFilterTest {

    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        root = File(context.cacheDir, "filter_test").apply { deleteRecursively(); mkdirs() }
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        helper = FrameworkSQLiteOpenHelperFactory().create(
            SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build(),
        )
        db = helper.writableDatabase
    }

    @After
    fun close() {
        helper.close()
        root.deleteRecursively()
    }

    /** Copies a test clip into its own video folder, adds its videos row and pulls its frames. */
    private fun addAndSplit(asset: String, videoId: String, durationS: Double) {
        val folder = File(root, videoId).apply { mkdirs() }
        val file = File(folder, "$videoId.mp4")
        InstrumentationRegistry.getInstrumentation().context.assets.open(asset).use { input ->
            file.outputStream().use { input.copyTo(it) }
        }
        VideoRepository { db }.insert(
            Video(videoId = videoId, filePath = file.absolutePath, recordedAt = "2026-10-12T16:00:00Z", createdAt = "2026-10-12T16:00:00Z", durationS = durationS),
        )
        VideoSplit.run(db, videoId)
    }

    private fun decisions(videoId: String): List<Triple<Int, Int, String?>> =
        db.query("SELECT frame_no, kept, drop_reason FROM frames WHERE video_id = ? ORDER BY frame_no", arrayOf(videoId)).use { cursor ->
            buildList { while (cursor.moveToNext()) add(Triple(cursor.getInt(0), cursor.getInt(1), if (cursor.isNull(2)) null else cursor.getString(2))) }
        }

    @Test
    fun anUnchangingPictureKeepsOnlyItsFirstFrame() {
        addAndSplit("test_clip_still.mp4", "still", 5.0)
        VideoFilter.run(db, "still")

        val rows = decisions("still")
        assertEquals(15, rows.size)
        assertEquals(Triple(1, 1, null), rows.first())
        assertTrue(rows.drop(1).all { it.second == 0 && it.third == "still" })
        // dropped frames keep their files: later cards and the panel need to see why they were dropped
        assertEquals(15, File(root, "still/frames").listFiles()!!.size)
    }

    @Test
    fun everyDroppedFrameHasAReasonAndEveryKeptFrameHasNone() {
        addAndSplit("test_clip.mp4", "moving", 10.0)
        VideoFilter.run(db, "moving")

        val rows = decisions("moving")
        assertEquals(30, rows.size)
        assertEquals(1, rows.first().second) // the first good frame is always kept
        rows.forEach { (frameNo, kept, reason) ->
            assertTrue("frame $frameNo", (kept == 1) == (reason == null))
            assertTrue("frame $frameNo: $reason", reason == null || reason in setOf("dark", "bright", "blurry", "still"))
        }
    }

    @Test
    fun runningTheStageAgainGivesTheSameDecisionsWhateverWasThereBefore() {
        addAndSplit("test_clip_still.mp4", "still", 5.0)
        VideoFilter.run(db, "still")
        val first = decisions("still")

        db.execSQL("UPDATE frames SET kept = 0, drop_reason = 'something old' WHERE video_id = 'still' AND frame_no = 1")
        db.execSQL("UPDATE frames SET kept = 1, drop_reason = NULL WHERE video_id = 'still' AND frame_no = 2")
        VideoFilter.run(db, "still")

        assertEquals(first, decisions("still"))
    }

    @Test
    fun theWholeJobRunsBothStagesThroughTheWorker() {
        val folder = File(root, "job").apply { mkdirs() }
        val file = File(folder, "job.mp4")
        InstrumentationRegistry.getInstrumentation().context.assets.open("test_clip_still.mp4").use { input ->
            file.outputStream().use { input.copyTo(it) }
        }
        VideoRepository { db }.insert(
            Video(videoId = "job", filePath = file.absolutePath, recordedAt = "2026-10-12T16:00:00Z", createdAt = "2026-10-12T16:00:00Z", durationS = 5.0),
        )
        val jobs = VideoJobs { db }
        jobs.enqueue("job")
        VideoWorker({ db }, jobs).drain()

        val (status, stage) = db.query("SELECT status, stage FROM jobs WHERE video_id = 'job'").use { it.moveToFirst(); it.getString(0) to it.getString(1) }
        assertEquals("done", status)
        assertEquals(VideoPipeline.STAGES.last().first, stage)
        assertEquals(1, decisions("job").count { it.second == 1 })
    }
}
