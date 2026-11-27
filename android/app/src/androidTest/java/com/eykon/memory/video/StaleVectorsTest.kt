package com.eykon.memory.video

import android.content.Context
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Decision re-check (26 Nov): ADR 0001's "has the table changed?" check reads MAX(id), and "any code that deletes vectors
 * must call VideoVectors.forget". A rerun of the split stage deletes a video's frames, and their image vectors go by
 * cascade, so nobody called forget. For a video that is not the newest, the search file then kept the deleted rows.
 * This test reruns the split stage's cleanup on the middle one of three videos and checks the search file holds only live rows (three videos, the middle one rerun).
 * Own test database, deleted at the end.
 */
@RunWith(AndroidJUnit4::class)
class StaleVectorsTest {

    private val name = "eyko_recheck_stale.db"
    private val context: Context = ApplicationProvider.getApplicationContext()

    private fun open(): SupportSQLiteOpenHelper = FrameworkSQLiteOpenHelperFactory().create(
        SupportSQLiteOpenHelper.Configuration.builder(context).name(name).callback(object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
            override fun onOpen(db: SupportSQLiteDatabase) = db.execSQL("PRAGMA foreign_keys = ON") // as MemoryDatabase does
        }).build(),
    )

    private fun vector(seed: Int) = FloatArray(512) { kotlin.math.sin(seed * 31.0 + it).toFloat() }.let { v ->
        val n = kotlin.math.sqrt(v.sumOf { (it * it).toDouble() }).toFloat(); FloatArray(512) { v[it] / n }
    }

    private fun addFrames(db: SupportSQLiteDatabase, video: String, count: Int): List<Long> = List(count) { i ->
        db.execSQL("INSERT INTO frames (video_id, frame_no, t_s, path) VALUES (?, ?, ?, ?)", arrayOf(video, i + 1, i / 3.0, "$video/f$i.jpg"))
        db.query("SELECT last_insert_rowid()").use { it.moveToFirst(); it.getLong(0) }
    }

    @Test
    fun rerunningTheSplitOfAnOlderVideoLeavesNoDeletedRowsInTheSearchFile() = rerun(fixed = true)

    /** The cleanup as it was before 26 Nov (sightings, then DELETE FROM frames): shows the bug the fix removes. */
    @Test
    fun theOldCleanupLeftDeletedRowsInTheSearchFile() = rerun(fixed = false)

    private fun rerun(fixed: Boolean) {
        context.deleteDatabase(name)
        val helper = open()
        val db = helper.writableDatabase
        val modeBefore = VideoVectors.mode
        try {
            for (v in listOf("A", "B", "C")) db.execSQL(
                "INSERT INTO videos (video_id, file_path, recorded_at, created_at) VALUES (?, ?, '2026-11-26T10:00:00Z', '2026-11-26T10:00:00Z')",
                arrayOf(v, "/x/$v/v.mp4"),
            )
            // three videos: the file's own check reads its first and last rows, so the rerun is of the MIDDLE video, B
            val all = addFrames(db, "A", 5) + addFrames(db, "B", 5) + addFrames(db, "C", 5)
            all.forEach { VideoVectors.put(db, "image_vec", it, vector(it.toInt())) }
            VideoVectors.mode = VectorMode.MAPPED_F32 // the mapped file path; NEON is not needed for ids
            VideoVectors.clearCache()
            assertEquals(15, VideoVectors.scores(db, "image_vec", vector(1)).ids.size) // the search file now holds 15 rows

            // the split stage reruns for A (the older video): its cleanup, then new frames; then embed_images as it does it
            if (fixed) VideoSplit.clearEarlierRun(db, "B") else {
                VideoLatest.forget(db, "B")
                db.execSQL("DELETE FROM frames WHERE video_id = ?", arrayOf("B"))
            }
            val b2 = addFrames(db, "B", 5)
            if (db.delete("image_vec", "frame_id IN (SELECT id FROM frames WHERE video_id = ?)", arrayOf("B")) > 0) VideoVectors.forget(db, "image_vec")
            b2.forEach { VideoVectors.put(db, "image_vec", it, vector(100 + it.toInt())) }
            VideoVectors.clearCache("image_vec")

            val live = db.query("SELECT frame_id FROM image_vec").use { c -> buildSet { while (c.moveToNext()) add(c.getLong(0)) } }
            val inFile = VideoVectors.scores(db, "image_vec", vector(1)).ids.toList()
            val stale = inFile.filter { it !in live }
            Log.i("EYKO_STALE", "${if (fixed) "fixed" else "old"} cleanup: rows in the search file ${inFile.size}, live rows ${live.size}, deleted rows still in the file: $stale")
            if (fixed) {
                assertEquals("deleted rows still in the search file", emptyList<Long>(), stale)
                assertEquals(live.sorted(), inFile.sorted())
            } else {
                assertEquals("the old cleanup should leave B's five old rows (the bug)", 5, stale.size)
            }
        } finally {
            VideoVectors.mode = modeBefore
            VideoVectors.clearCache()
            helper.close()
            context.deleteDatabase(name)
            listOf("image_vec", "text_vec", "audio_vec").forEach { t ->
                listOf("vec", "ids").forEach { java.io.File("${context.getDatabasePath(name).path}.$t.$it").delete() }
            }
        }
    }
}
