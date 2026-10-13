package com.eykon.memory.video

import android.content.Context
import android.media.MediaMetadataRetriever
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.vision.ImageEmbedder
import com.eykon.memory.ml.vision.ObjectDetector
import com.eykon.memory.ml.vision.TextEmbedder
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
 * Search by typed phrase over stored frame vectors, on a real phone. Tests named
 * "...WithTheRealModel(s)" need the model files in the phone's models folder.
 */
@RunWith(AndroidJUnit4::class)
class VideoSearchTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        root = File(context.cacheDir, "search_test").apply { deleteRecursively(); mkdirs() }
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
    private fun along(direction: Int) = FloatArray(ImageEmbedder.DIMENSIONS).also { it[direction] = 1f }

    /** test_clip_repeat.mp4 with stand-in vectors: frame 1 points along direction 0, frame 4 along direction 1. */
    private fun prepare(videoId: String) {
        val folder = File(root, videoId).apply { mkdirs() }
        val file = File(folder, "$videoId.mp4")
        testAssets.open("test_clip_repeat.mp4").use { input -> file.outputStream().use { input.copyTo(it) } }
        VideoRepository { db }.insert(Video(videoId = videoId, filePath = file.absolutePath, recordedAt = "2026-10-13T17:00:00Z", createdAt = "2026-10-13T17:00:00Z", durationS = 4.0))
        VideoSplit.run(db, videoId)
        VideoFilter.run(db, videoId, 1)
        var next = 0
        VideoDedup.run(db, videoId) { along(next++) }
        VideoScene.run(db, videoId, "A") { f, _ -> Perception(emptyList(), null, null, 0, caption = "caption of ${f.name}") }
        VideoEmbedImages.run(db, videoId) { throw AssertionError("vectors are saved") }
        VideoFinish.run(db, videoId) // only ready videos are searched
    }

    // ── The search's rules, with a stand-in for the text model ──────────────────

    @Test
    fun theFrameThatPointsTheSameWayAsThePhraseComesFirst() {
        prepare("clip")
        val hits = VideoSearch.frames(db, "second picture", 20) { along(1) }

        assertEquals(2, hits.size) // only two frames are stored
        val best = hits.first()
        assertEquals(1f, best.score, 1e-6f)
        assertEquals("clip", best.videoId)
        assertEquals("2026-10-13T17:00:00Z", best.recordedAt)
        assertEquals(1.0, best.tS, 0.01) // frame 4 of a 3-per-second clip
        assertEquals("000004.jpg", best.file.name)
        assertTrue("the frame file can be opened", best.file.exists())
        assertEquals("caption of 000004.jpg", best.caption)
        assertEquals(0f, hits[1].score, 1e-6f)
    }

    @Test
    fun onlyAsManyHitsAsAskedForComeBack() {
        prepare("clip")
        assertEquals(1, VideoSearch.frames(db, "anything", 1) { along(0) }.size)
    }

    @Test
    fun anEmptyPhraseOrAnEmptyStoreGivesNothingAndTheModelIsNotAsked() {
        assertEquals(emptyList<FrameHit>(), VideoSearch.frames(db, "a helmet", 20) { along(0) })
        prepare("clip")
        assertEquals(emptyList<FrameHit>(), VideoSearch.frames(db, "   ", 20) { throw AssertionError("nothing to embed") })
    }

    // ── The real text model on this phone ───────────────────────────────────────

    @Test
    fun thePhoneGivesTheSameTextVectorsAsTheLaptopWithTheRealModel() {
        assumeTrue("text model not on this phone", TextEmbedder.modelFile(context).exists())
        val golden = Json.parseToJsonElement(testAssets.open("clip_text_golden.json").bufferedReader().readText()).jsonObject
        for ((sentence, expected) in golden["vectors"]!!.jsonObject) {
            val laptop = expected.jsonArray.map { it.jsonPrimitive.float }
            val phone = TextEmbedder.embed(context, sentence)
            assertEquals(ImageEmbedder.DIMENSIONS, phone.size)
            val cosine = phone.indices.sumOf { phone[it].toDouble() * laptop[it] }
            Log.i("EykonVideo", "text parity \"${sentence.trim().take(40)}\": cosine with the laptop %.5f".format(cosine))
            assertTrue("$sentence: phone and laptop agree only $cosine", cosine > 0.999)
        }
        val times = List(10) { System.nanoTime().let { start -> TextEmbedder.embed(context, "where are my keys"); (System.nanoTime() - start) / 1_000_000 } }.sorted()
        Log.i("EykonVideo", "text speed: median ${times[5]} ms, worst ${times.last()} ms per phrase over 10 runs; native ${android.os.Debug.getNativeHeapAllocatedSize() / 1_000_000} MB")
    }

    /**
     * Not pass/fail: the same search the Video tab runs, over the videos already in the app on this
     * phone. Only reads. The hits go to logcat (tag EykonVideo). Phrases: -e phrases "a helmet|a racket".
     */
    @Test
    fun typedPhrasesOverTheAppsOwnVideosWithTheRealModel() {
        assumeTrue("text model not on this phone", TextEmbedder.modelFile(context).exists())
        val appDb = com.eykon.memory.MemoryApp.instance.database.openHelper.writableDatabase
        val stored = appDb.query("SELECT COUNT(*), COUNT(DISTINCT f.video_id) FROM image_vec i JOIN frames f ON f.id = i.frame_id").use { it.moveToFirst(); it.getInt(0) to it.getInt(1) }
        Log.i("EykonVideo", "app search: ${stored.first} frame vectors from ${stored.second} videos are stored in the app")
        assumeTrue("the app has no stored frame vectors yet", stored.first > 0)
        for (phrase in (InstrumentationRegistry.getArguments().getString("phrases") ?: "a helmet").split("|")) {
            val start = System.nanoTime()
            val hits = VideoSearch.frames(appDb, phrase, 5)
            val ms = (System.nanoTime() - start) / 1_000_000
            Log.i("EykonVideo", "app search \"$phrase\" ($ms ms): " + hits.joinToString("; ") { "%s %.1f s %.3f [%s]".format(it.videoId.take(8), it.tS, it.score, it.caption) })
            assertTrue(hits.all { it.file.exists() })
        }
    }

    /** Not pass/fail: a real clip through the whole job, then real phrases; the hits go to logcat (tag EykonVideo). */
    @Test
    fun typedPhrasesOverARealClipWithTheRealModels() {
        val clip = File(context.getExternalFilesDir(null), "eval_clips/" + (InstrumentationRegistry.getArguments().getString("clip") ?: "clip4.mp4"))
        val phrases = (InstrumentationRegistry.getArguments().getString("phrases") ?: "a backpack|a laptop|a red chair|people laughing").split("|")
        assumeTrue(
            "models or ${clip.name} not on this phone",
            clip.exists() && TextEmbedder.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists() && ObjectDetector.modelFile(context).exists() && com.eykon.memory.ml.embedder.BgeEmbedder.modelFile(context).exists(),
        )
        val folder = File(root, "real").apply { mkdirs() }
        val copy = File(folder, "real.mp4").also { clip.copyTo(it, overwrite = true) }
        val length = MediaMetadataRetriever().run { setDataSource(copy.absolutePath); (extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)!!.toLong() / 1000.0).also { release() } }
        VideoRepository { db }.insert(Video(videoId = "real", filePath = copy.absolutePath, recordedAt = "2026-10-13T17:00:00Z", createdAt = "2026-10-13T17:00:00Z", durationS = length))
        val jobs = VideoJobs { db }
        jobs.enqueue("real")
        VideoWorker({ db }, jobs).drain()

        for (phrase in phrases) {
            val start = System.nanoTime()
            val hits = VideoSearch.frames(db, phrase, 3)
            val ms = (System.nanoTime() - start) / 1_000_000
            Log.i("EykonVideo", "search ${clip.name} \"$phrase\" ($ms ms): " + hits.joinToString("; ") { "%.1f s %.3f".format(it.tS, it.score) })
            assertTrue(hits.isNotEmpty() && hits.zipWithNext().all { (a, b) -> a.score >= b.score })
        }
    }
}
