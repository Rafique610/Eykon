package com.eykon.memory.video

import android.content.Context
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.embedder.BgeEmbedder
import com.eykon.memory.ml.vision.ImageEmbedder
import com.eykon.memory.ml.vision.ObjectDetector
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * The embed_texts stage on a real phone. Tests named "...WithTheRealModel(s)" need the model
 * files in the phone's models folder.
 */
@RunWith(AndroidJUnit4::class)
class VideoEmbedTextsTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        root = File(context.cacheDir, "embed_texts_test").apply { deleteRecursively(); mkdirs() }
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        helper = FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build())
        db = helper.writableDatabase
        VideoVectors.clearCache()
    }

    @After
    fun close() {
        helper.close()
        root.deleteRecursively()
        VideoVectors.clearCache()
    }

    private val testAssets get() = InstrumentationRegistry.getInstrumentation().context.assets

    /** A stand-in for the model: texts with the same first letter point the same way. */
    private val byFirstLetter: (String) -> FloatArray = { text -> FloatArray(BgeEmbedder.DIMENSIONS).also { it[text.first().code % BgeEmbedder.DIMENSIONS] = 1f } }

    private fun addVideo(videoId: String) {
        val folder = File(root, videoId).apply { mkdirs() }
        val file = File(folder, "$videoId.mp4")
        testAssets.open("test_clip_repeat.mp4").use { input -> file.outputStream().use { input.copyTo(it) } }
        VideoRepository { db }.insert(Video(videoId = videoId, filePath = file.absolutePath, recordedAt = "2026-10-13T18:00:00Z", createdAt = "2026-10-13T18:00:00Z", durationS = 4.0))
    }

    /** Two kept frames (1 and 4), captioned "keys on a table" and "laptop, in an office". */
    private fun prepare(videoId: String, captions: List<String> = listOf("keys on a table", "laptop, in an office")) {
        addVideo(videoId)
        VideoSplit.run(db, videoId)
        VideoFilter.run(db, videoId, 1)
        var next = 0
        VideoDedup.run(db, videoId) { FloatArray(ImageEmbedder.DIMENSIONS).also { it[next++] = 1f } }
        var caption = 0
        VideoScene.run(db, videoId, "A") { _, _ -> Perception(emptyList(), null, null, 0, caption = captions[caption++]) }
    }

    private class Row(val id: Long, val source: String, val refId: Long, val startS: Double, val endS: Double, val text: String)

    private fun texts(videoId: String) =
        db.query("SELECT id, source, ref_id, start_s, end_s, text FROM video_texts WHERE video_id = ? ORDER BY start_s, id", arrayOf(videoId)).use { c ->
            buildList { while (c.moveToNext()) add(Row(c.getLong(0), c.getString(1), c.getLong(2), c.getDouble(3), c.getDouble(4), c.getString(5))) }
        }

    private fun found(word: String) =
        db.query("SELECT docid FROM video_texts_fts WHERE video_texts_fts MATCH ? ORDER BY docid", arrayOf(word)).use { c -> buildList { while (c.moveToNext()) add(c.getLong(0)) } }

    private fun count(table: String) = db.query("SELECT COUNT(*) FROM $table").use { it.moveToFirst(); it.getInt(0) }

    // ── The stage's rules, with a stand-in for the model ────────────────────────

    @Test
    fun everyCaptionBecomesATextRowAKeywordEntryAndAVector() {
        prepare("clip")
        VideoEmbedTexts.run(db, "clip", byFirstLetter)

        val rows = texts("clip")
        assertEquals(listOf("keys on a table", "laptop, in an office"), rows.map { it.text })
        val frames = db.query("SELECT id, t_s FROM frames WHERE video_id = 'clip' AND kept = 1 ORDER BY t_s").use { c -> buildList { while (c.moveToNext()) add(c.getLong(0) to c.getDouble(1)) } }
        rows.zip(frames).forEach { (row, frame) ->
            assertEquals("caption", row.source)
            assertEquals(frame.first, row.refId)
            assertEquals(frame.second, row.startS, 1e-9)
            assertEquals(frame.second, row.endS, 1e-9)
        }
        assertEquals(2, count("text_vec"))
        assertEquals(0, count("transcript_chunks")) // a video with no speech is normal
    }

    @Test
    fun aWordFromACaptionIsFoundByKeyword() {
        prepare("clip")
        VideoEmbedTexts.run(db, "clip", byFirstLetter)
        val rows = texts("clip")

        assertEquals(listOf(rows[0].id), found("keys"))
        assertEquals(listOf(rows[1].id), found("office"))
        assertEquals(emptyList<Long>(), found("helmet"))
    }

    @Test
    fun aCaptionsOwnVectorFindsThatCaptionFirst() {
        prepare("clip")
        VideoEmbedTexts.run(db, "clip", byFirstLetter)
        val laptop = texts("clip")[1]

        assertEquals(laptop.id to 1f, VideoVectors.knn(db, "text_vec", byFirstLetter("laptop, in an office"), 1).single())
    }

    @Test
    fun transcriptChunksJoinOnceTheyExist() {
        prepare("clip")
        db.execSQL("INSERT INTO transcript_chunks (video_id, start_s, end_s, text) VALUES ('clip', 0.5, 2.5, 'remember to buy milk')")
        VideoEmbedTexts.run(db, "clip", byFirstLetter)

        val rows = texts("clip")
        assertEquals(listOf("caption", "transcript", "caption"), rows.map { it.source })
        val said = rows.single { it.source == "transcript" }
        assertEquals(listOf(0.5, 2.5), listOf(said.startS, said.endS))
        assertEquals(listOf(said.id), found("milk"))
        assertEquals(3, count("text_vec"))
    }

    @Test
    fun runningTheStageAgainLeavesNoCopies() {
        prepare("clip")
        VideoEmbedTexts.run(db, "clip", byFirstLetter)
        VideoEmbedTexts.run(db, "clip", byFirstLetter)

        assertEquals(2, texts("clip").size)
        assertEquals(2, count("text_vec"))
        assertEquals(1, found("keys").size)
    }

    @Test
    fun aVideoWithNothingToSayWritesNothing() {
        addVideo("empty")
        VideoEmbedTexts.run(db, "empty") { throw AssertionError("nothing to embed") }
        assertEquals(0, count("video_texts"))
        assertEquals(0, count("text_vec"))
    }

    @Test
    fun deletingTheVideoRemovesItsTextsKeywordsAndVectors() {
        prepare("clip")
        VideoEmbedTexts.run(db, "clip", byFirstLetter)
        db.execSQL("DELETE FROM videos WHERE video_id = 'clip'")

        assertEquals(0, count("video_texts"))
        assertEquals(0, count("text_vec"))
        assertEquals(emptyList<Long>(), found("keys"))
    }

    // ── The real model on this phone ─────────────────────────────────────────────

    @Test
    fun thePhoneGivesTheSameVectorsAsTheLaptopWithTheRealModel() {
        assumeTrue("text embedder not on this phone", BgeEmbedder.modelFile(context).exists())
        val golden = Json.parseToJsonElement(testAssets.open("bge_golden.json").bufferedReader().readText()).jsonObject
        for ((sentence, expected) in golden["vectors"]!!.jsonObject) {
            val laptop = expected.jsonArray.map { it.jsonPrimitive.float }
            val phone = BgeEmbedder.embed(context, sentence)
            assertEquals(BgeEmbedder.DIMENSIONS, phone.size)
            val cosine = phone.indices.sumOf { phone[it].toDouble() * laptop[it] }
            Log.i("EykonVideo", "bge parity \"${sentence.trim().take(40)}\": cosine with the laptop %.5f".format(cosine))
            assertTrue("$sentence: phone and laptop agree only $cosine", cosine > 0.999)
        }
        val times = List(10) { System.nanoTime().let { start -> BgeEmbedder.embed(context, "laptop, chair and keyboard, 7 people, in a classroom, typing on a laptop"); (System.nanoTime() - start) / 1_000_000 } }.sorted()
        Log.i("EykonVideo", "bge speed: median ${times[5]} ms, worst ${times.last()} ms per caption over 10 runs")
    }

    @Test
    fun theWholeJobMakesEveryCaptionSearchableWithTheRealModels() {
        assumeTrue(
            "models not on this phone",
            ObjectDetector.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists() && BgeEmbedder.modelFile(context).exists(),
        )
        addVideo("job")
        val jobs = VideoJobs { db }
        jobs.enqueue("job")
        VideoWorker({ db }, jobs).drain()

        val (status, stage, error) = db.query("SELECT status, stage, error FROM jobs WHERE video_id = 'job'").use { it.moveToFirst(); Triple(it.getString(0), it.getString(1), it.getString(2)) }
        assertEquals("job error: $error", "done", status)
        assertEquals(VideoPipeline.STAGES.last().first, stage)
        val rows = texts("job")
        assertEquals(count("scene_records"), rows.size)
        assertEquals(rows.size, count("text_vec"))
        rows.forEach { row ->
            assertEquals(row.id, VideoVectors.knn(db, "text_vec", BgeEmbedder.embed(context, row.text), 1).single().first.let { best ->
                // two frames may share one caption word for word; then either row is a right answer
                if (rows.first { it.id == best }.text == row.text) row.id else best
            })
        }
    }
}
