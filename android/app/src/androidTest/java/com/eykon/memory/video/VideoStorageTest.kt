package com.eykon.memory.video

import android.content.Context
import android.database.sqlite.SQLiteConstraintException
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** The video tables and the repository, on the phone's own SQLite, in an in-memory database. */
@RunWith(AndroidJUnit4::class)
class VideoStorageTest {

    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
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
        repository = VideoRepository { db }
    }

    @After
    fun close() = helper.close()

    private fun count(table: String): Long =
        db.query("SELECT COUNT(*) FROM $table").use { it.moveToFirst(); it.getLong(0) }

    private fun video(id: String = "v1") = Video(
        videoId = id, filePath = "/videos/$id/$id.mp4",
        recordedAt = "2026-10-07T18:42:00Z", createdAt = "2026-10-12T15:00:00Z", durationS = 62.0,
    )

    @Test
    fun creatingTwiceChangesNothingAndAllTablesExist() {
        VideoSchema.create(db)
        VideoSchema.TABLES.forEach { table -> assertEquals(table, 0L, count(table)) }
    }

    @Test
    fun aVideoRoundTripsThroughTheRepository() {
        repository.insert(video().copy(lat = 24.8607, lon = 67.0011))
        repository.insert(video("v2"))

        val saved = repository.get("v1")!!
        assertEquals("processing", saved.status)
        assertEquals(62.0, saved.durationS, 1e-9)
        assertEquals(24.8607, saved.lat!!, 1e-9)
        assertNull(repository.get("v2")!!.lat)
        assertNull(repository.get("missing"))
        assertEquals(2, repository.list().size)
    }

    @Test
    fun aFrameNeedsAnExistingVideo() {
        assertThrows(SQLiteConstraintException::class.java) {
            db.execSQL("INSERT INTO frames (video_id, frame_no, t_s, path) VALUES (?, ?, ?, ?)", arrayOf("missing", 1, 0.0, "1.jpg"))
        }
    }

    @Test
    fun deletingAVideoRemovesEverythingThatBelongsToIt() {
        repository.insert(video())
        db.execSQL("INSERT INTO frames (id, video_id, frame_no, t_s, path) VALUES (1, 'v1', 1, 0.0, '1.jpg')")
        db.execSQL("INSERT INTO image_vec (frame_id, embedding) VALUES (1, ?)", arrayOf(ByteArray(8)))
        db.execSQL("INSERT INTO scene_records (frame_id, objects, caption, source) VALUES (1, '[]', 'a desk', 'A')")
        db.execSQL("INSERT INTO video_texts (id, video_id, source, ref_id, start_s, end_s, text) VALUES (1, 'v1', 'caption', 1, 0, 0, 'keys on the hall table')")
        db.execSQL("INSERT INTO text_vec (text_id, embedding) VALUES (1, ?)", arrayOf(ByteArray(8)))
        val found = db.query("SELECT docid FROM video_texts_fts WHERE video_texts_fts MATCH ?", arrayOf("keys")).use { it.count }
        assertEquals(1, found)

        // an edited text is found by its new words and no longer by its old ones
        db.execSQL("UPDATE video_texts SET text = ? WHERE id = 1", arrayOf("wallet on the desk"))
        assertEquals(0, db.query("SELECT docid FROM video_texts_fts WHERE video_texts_fts MATCH ?", arrayOf("keys")).use { it.count })
        assertEquals(1, db.query("SELECT docid FROM video_texts_fts WHERE video_texts_fts MATCH ?", arrayOf("wallet")).use { it.count })

        db.execSQL("DELETE FROM videos WHERE video_id = ?", arrayOf("v1"))

        listOf("videos", "frames", "image_vec", "scene_records", "video_texts", "text_vec").forEach { table ->
            assertEquals(table, 0L, count(table))
        }
        val left = db.query("SELECT docid FROM video_texts_fts WHERE video_texts_fts MATCH ?", arrayOf("wallet")).use { it.count }
        assertTrue(left == 0)
    }
}
