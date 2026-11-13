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
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Card EYKO-71: the same file added twice gives one row and a message; a different file still works; a file over the
 * limit is refused before any copying; a database made before the content_hash column gets it. The database is in
 * memory; the copies go to the app's own videos folder and every folder this test makes is deleted at the end.
 */
@RunWith(AndroidJUnit4::class)
class VideoCaptureTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var repository: VideoRepository
    private lateinit var capture: VideoCapture
    private val videosRoot get() = File(context.filesDir, "videos")
    private var foldersBefore = emptySet<String>()

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        helper = openHelper { VideoSchema.create(it) }
        db = helper.writableDatabase
        repository = VideoRepository { db }
        capture = VideoCapture(context, repository, VideoJobs { db })
        foldersBefore = videosRoot.list()?.toSet() ?: emptySet()
    }

    @After
    fun close() {
        (videosRoot.list()?.toSet() ?: emptySet()).minus(foldersBefore).forEach { File(videosRoot, it).deleteRecursively() }
        helper.close()
    }

    private fun openHelper(onCreate: (SupportSQLiteDatabase) -> Unit): SupportSQLiteOpenHelper {
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = onCreate(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        return FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build())
    }

    private fun add(asset: String): SavedVideo =
        capture.saveStream("mp4", null) { InstrumentationRegistry.getInstrumentation().context.assets.open(asset) }

    private fun count(table: String): Int = db.query("SELECT COUNT(*) FROM $table").use { it.moveToFirst(); it.getInt(0) }

    @Test
    fun theSameFileAddedTwiceGivesOneRowAndTheMessage() {
        val first = add("test_clip.mp4")
        assertNotNull(first.video.contentHash)
        assertEquals(64, first.video.contentHash!!.length)

        try {
            add("test_clip.mp4")
            fail("the second copy of the same file should be refused")
        } catch (e: UploadException) {
            assertTrue(e.message, e.message!!.startsWith("This video is already saved (recorded "))
        }

        assertEquals(1, count("videos"))
        assertEquals(1, count("jobs"))
        val folders = (videosRoot.list()?.toSet() ?: emptySet()).minus(foldersBefore)
        assertEquals("the refused copy must not leave a folder", setOf(first.video.videoId), folders)
    }

    @Test
    fun aDifferentFileStillWorksAndGetsItsOwnHash() {
        val one = add("test_clip.mp4")
        val two = add("test_clip_still.mp4")
        assertEquals(2, count("videos"))
        assertTrue(one.video.contentHash != two.video.contentHash)
        assertEquals(one.video.videoId, repository.findByHash(one.video.contentHash!!)!!.videoId)
        assertNull(repository.findByHash("0".repeat(64)))
    }

    @Test
    fun aFileOverTheLimitIsRefusedBeforeAnyCopying() {
        var opened = false
        try {
            capture.saveStream("mp4", 501L * 1024 * 1024) { opened = true; InstrumentationRegistry.getInstrumentation().context.assets.open("test_clip.mp4") }
            fail("expected a refusal")
        } catch (e: UploadException) {
            assertEquals("This file is larger than the limit of 500 MB.", e.message)
        }
        assertFalse("the file must not even be opened", opened)
        assertEquals(0, count("videos"))
        assertTrue((videosRoot.list()?.toSet() ?: emptySet()).minus(foldersBefore).isEmpty())
    }

    @Test
    fun aDatabaseMadeBeforeTheColumnExistedGetsItWithOldRowsLeftAloneAndItIsSafeToRepeat() {
        val old = openHelper {
            it.execSQL(
                """CREATE TABLE videos (video_id TEXT PRIMARY KEY, file_path TEXT NOT NULL, recorded_at TEXT NOT NULL,
                   duration_s REAL NOT NULL DEFAULT 0, lat REAL, lon REAL,
                   status TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')), created_at TEXT NOT NULL)""",
            )
            it.execSQL("INSERT INTO videos (video_id, file_path, recorded_at, created_at) VALUES ('old1', 'x.mp4', '2026-10-01T10:00:00Z', '2026-10-01T10:00:00Z')")
        }
        try {
            val oldDb = old.writableDatabase
            VideoSchema.create(oldDb)
            VideoSchema.create(oldDb) // every open runs it again
            val columns = oldDb.query("PRAGMA table_info(videos)").use { c -> buildList { while (c.moveToNext()) add(c.getString(1)) } }
            // EYKO-71 content_hash, then EYKO-126 source_uri and display_name, in the CREATE TABLE's order
            assertEquals(listOf("content_hash", "source_uri", "display_name"), columns.takeLast(3))
            val oldRow = VideoRepository { oldDb }.get("old1")!!
            assertNull(oldRow.contentHash)
            assertNull(oldRow.sourceUri)
            assertNull(oldRow.displayName)
            val indexes = oldDb.query("PRAGMA index_list(videos)").use { c -> buildList { while (c.moveToNext()) add(c.getString(1)) } }
            assertTrue(indexes.contains("videos_content_hash"))
        } finally {
            old.close()
        }
    }
}
