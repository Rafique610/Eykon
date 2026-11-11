package com.eykon.memory.video

import android.content.Context
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.embedder.BgeEmbedder
import com.eykon.memory.ml.vision.Detection
import com.eykon.memory.ml.vision.ImageEmbedder
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Card EYKO-119, supervisor question C1: "does a resumed stage give the same rows as a clean run?"
 *
 * Real stages on a real phone's SQLite, with stand-ins for the models. A clean run of the whole pipeline is
 * the reference. Then each stage is hit by the two ways a job can be cut short, and the whole result (every
 * table, every vector, the files in the video's folder) must equal the reference:
 *  1. the app dies after a stage wrote its rows but before the job saved it as done, so the stage runs again;
 *  2. a stage dies half-way (an exception inside the model calls), then runs again.
 */
@RunWith(AndroidJUnit4::class)
class VideoRerunSafetyTest {

    private lateinit var context: Context
    private lateinit var root: File
    private val helpers = ArrayList<SupportSQLiteOpenHelper>()
    private var runs = 0

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        root = File(context.cacheDir, "rerun_test").apply { deleteRecursively(); mkdirs() }
    }

    @After
    fun close() {
        helpers.forEach { it.close() }
        root.deleteRecursively()
    }

    private val testAssets get() = InstrumentationRegistry.getInstrumentation().context.assets

    private class Run(val db: SupportSQLiteDatabase, val folder: File)

    /** An empty database and a copy of test_clip_repeat.mp4 (4 s: A, B, A, B) added the way the picker does. */
    private fun freshRun(): Run {
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        val helper = FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build())
        helpers.add(helper)
        val db = helper.writableDatabase
        val folder = File(File(root, "r${runs++}").apply { mkdirs() }, VIDEO).apply { mkdirs() }
        val file = File(folder, "$VIDEO.mp4")
        testAssets.open("test_clip_repeat.mp4").use { input -> file.outputStream().use { input.copyTo(it) } }
        VideoRepository { db }.insert(
            Video(videoId = VIDEO, filePath = file.absolutePath, recordedAt = "2026-10-13T16:00:00Z", createdAt = "2026-10-13T16:00:00Z", durationS = 4.0),
        )
        return Run(db, folder)
    }

    /** Counts the calls to the stand-in models of one stage and makes one of them throw, like a crash half-way. */
    private class Calls {
        var target: String? = null
        var failOn = -1
        var count = 0
        var died = false

        fun tick(stage: String) {
            if (stage != target) return
            count++
            if (count == failOn) {
                died = true
                throw IllegalStateException("simulated crash inside $stage")
            }
        }
    }

    /** The real stages in the pipeline's order; only the models are stand-ins. */
    private fun stages(calls: Calls): List<Pair<String, Stage>> = listOf(
        "split" to { db, id -> VideoSplit.run(db, id) },
        "filter" to { db, id -> VideoFilter.run(db, id, 1) },
        "dedup" to { db, id ->
            var next = 0
            VideoDedup.run(db, id) { calls.tick("dedup"); FloatArray(ImageEmbedder.DIMENSIONS).also { it[next++] = 1f } }
        },
        "scene" to { db, id ->
            VideoScene.run(db, id, "A") { _, _ ->
                calls.tick("scene")
                Perception(listOf(Detection("laptop", 0.8f, listOf(1f, 2f, 3f, 4f))), "typing on a laptop", "an office", 1)
            }
        },
        "small_objects" to { db, id ->
            VideoSmallObjects.run(db, id) { _, _ ->
                calls.tick("small_objects")
                listOf(Detection("keys", 0.6f, listOf(10f, 10f, 50f, 50f), "own"))
            }
        },
        "embed_images" to { db, id ->
            VideoEmbedImages.run(db, id) { calls.tick("embed_images"); FloatArray(ImageEmbedder.DIMENSIONS).also { it[0] = 1f } }
        },
        "embed_texts" to { db, id ->
            VideoEmbedTexts.run(db, id) { text -> calls.tick("embed_texts"); FloatArray(BgeEmbedder.DIMENSIONS).also { it[text.first().code % BgeEmbedder.DIMENSIONS] = 1f } }
        },
        "link" to { db, id -> VideoLink.run(db, id) },
        "latest" to { db, id ->
            VideoLatest.run(db, id, 0.87f) { _, box -> calls.tick("latest"); FloatArray(ImageEmbedder.DIMENSIONS).also { it[box[0].toInt()] = 1f } }
        },
        "finish" to { db, id -> VideoFinish.run(db, id) },
    )

    /** Everything a run leaves behind that does not depend on row numbers, as lines of text to compare. */
    private fun snapshot(run: Run): List<String> = buildList {
        fun table(name: String, sql: String) {
            run.db.query(sql).use { c ->
                add("$name: ${c.count} rows")
                while (c.moveToNext()) add("$name | " + (0 until c.columnCount).joinToString(" | ") { if (c.isNull(it)) "NULL" else c.getString(it) })
            }
        }
        table("videos", "SELECT status FROM videos")
        table("frames", "SELECT frame_no, printf('%.3f', t_s), path, kept, COALESCE(drop_reason, ''), COALESCE(phash, '') FROM frames ORDER BY frame_no")
        table("scene", "SELECT f.frame_no, s.objects, COALESCE(s.action, ''), COALESCE(s.place, ''), s.people, s.caption, s.source FROM scene_records s JOIN frames f ON f.id = s.frame_id ORDER BY f.frame_no")
        table("texts", "SELECT source, printf('%.3f', start_s), printf('%.3f', end_s), text FROM video_texts ORDER BY start_s, text")
        table("image_vec", "SELECT f.frame_no, hex(v.embedding) FROM image_vec v JOIN frames f ON f.id = v.frame_id ORDER BY f.frame_no")
        table("text_vec", "SELECT t.text, hex(v.embedding) FROM text_vec v JOIN video_texts t ON t.id = v.text_id ORDER BY t.start_s, t.text")
        table("sightings", "SELECT label, seen_at, COALESCE(place, ''), is_latest, hex(embedding) FROM object_sightings ORDER BY seen_at, label, hex(embedding)")
        add("frame files: " + (File(run.folder, "frames").list()?.sorted() ?: emptyList()).joinToString(","))
        add("audio bytes: " + File(run.folder, "audio16k.wav").let { if (it.exists()) it.length() else -1 })
        add("vectors file: " + File(run.folder, VideoDedup.VECTORS_FILE).let { if (it.exists()) it.length() else -1 })
    }

    private fun runAll(run: Run, stages: List<Pair<String, Stage>>) = stages.forEach { (_, stage) -> stage(run.db, VIDEO) }

    private fun cleanSnapshot(): List<String> {
        val run = freshRun()
        runAll(run, stages(Calls()))
        return snapshot(run)
    }

    @Test
    fun theCleanRunReachesReadyWithRowsInEveryTableSoTheComparisonsMeanSomething() {
        val clean = cleanSnapshot()
        assertTrue(clean.joinToString("\n"), clean.contains("videos | ready"))
        listOf("frames", "scene", "texts", "image_vec", "text_vec", "sightings").forEach { table ->
            assertTrue("$table is empty in the reference run", clean.none { it == "$table: 0 rows" })
        }
    }

    @Test
    fun everyStageRunTwiceInARowGivesTheSameResultAsOnce() {
        val clean = cleanSnapshot()
        val names = stages(Calls()).map { it.first }
        for (k in names.indices) {
            val run = freshRun()
            // The app died after stage k wrote its rows but before the job saved "k is done": stage k runs again.
            stages(Calls()).forEachIndexed { i, (_, stage) ->
                stage(run.db, VIDEO)
                if (i == k) stage(run.db, VIDEO)
            }
            assertEquals("stage ${names[k]} run twice", clean, snapshot(run))
        }
    }

    @Test
    fun aStageThatDiesHalfWayAndThenRunsAgainGivesTheSameResultAsOnce() {
        val clean = cleanSnapshot()
        // The stages whose stand-in model is called more than once; embed_images reuses dedup's saved vectors and never calls its model.
        for (name in listOf("dedup", "scene", "small_objects", "embed_texts", "latest")) {
            val run = freshRun()
            val calls = Calls().apply { target = name; failOn = 2 }
            for ((stageName, stage) in stages(calls)) {
                if (stageName == name) {
                    try {
                        stage(run.db, VIDEO)
                    } catch (e: IllegalStateException) {
                        assertTrue(e.message, e.message!!.startsWith("simulated crash"))
                    }
                    assertTrue("the stand-in never crashed inside $name", calls.died)
                    calls.target = null // the second run is clean
                }
                stage(run.db, VIDEO)
            }
            assertEquals("stage $name died half-way and ran again", clean, snapshot(run))
        }
    }

    @Test
    fun splitIgnoresWhatAnEarlierHalfFinishedRunLeftInTheFolderAndTheTable() {
        val clean = cleanSnapshot()
        val run = freshRun()
        File(run.folder, "frames").mkdirs()
        File(run.folder, "frames/000999.jpg").writeText("half a picture")
        File(run.folder, "audio16k.wav").writeText("half a sound")
        run.db.execSQL("INSERT INTO frames (video_id, frame_no, t_s, path) VALUES (?, 999, 99.0, ?)", arrayOf(VIDEO, "$VIDEO/frames/000999.jpg"))
        runAll(run, stages(Calls()))
        assertEquals(clean, snapshot(run))
    }

    private companion object {
        const val VIDEO = "clip"
    }
}
