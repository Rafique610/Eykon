package com.eykon.memory.video

import android.content.Context
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.vision.ImageEmbedder
import com.eykon.memory.ml.vision.ObjectDetector
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * The embed_images stage and vector search on a real phone. The test named
 * "...WithTheRealModels" needs the two model files in the phone's models folder.
 */
@RunWith(AndroidJUnit4::class)
class VideoEmbedImagesTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        root = File(context.cacheDir, "embed_images_test").apply { deleteRecursively(); mkdirs() }
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

    /** A vector of length 1 that points along one of the 512 directions. */
    private fun along(direction: Int) = FloatArray(ImageEmbedder.DIMENSIONS).also { it[direction] = 1f }

    private fun addVideo(videoId: String): File {
        val folder = File(root, videoId).apply { mkdirs() }
        val file = File(folder, "$videoId.mp4")
        testAssets.open("test_clip_repeat.mp4").use { input -> file.outputStream().use { input.copyTo(it) } }
        VideoRepository { db }.insert(Video(videoId = videoId, filePath = file.absolutePath, recordedAt = "2026-10-13T17:00:00Z", createdAt = "2026-10-13T17:00:00Z", durationS = 4.0))
        return folder
    }

    /** test_clip_repeat.mp4 (A, B, A, B) through split, filter and a stand-in dedup: frames 1 and 4 stay kept. */
    private fun prepare(videoId: String): File {
        val folder = addVideo(videoId)
        VideoSplit.run(db, videoId)
        VideoFilter.run(db, videoId, 1)
        var next = 0
        VideoDedup.run(db, videoId) { along(next++) }
        return folder
    }

    private fun keptIds(videoId: String) =
        db.query("SELECT id FROM frames WHERE video_id = ? AND kept = 1 ORDER BY t_s", arrayOf(videoId)).use { c -> buildList { while (c.moveToNext()) add(c.getLong(0)) } }

    private fun storedIds() =
        db.query("SELECT frame_id FROM image_vec ORDER BY frame_id").use { c -> buildList { while (c.moveToNext()) add(c.getLong(0)) } }

    private val neverCalled: (File) -> FloatArray = { throw AssertionError("a saved vector exists, the model must not run for ${it.name}") }

    // ── The stage ────────────────────────────────────────────────────────────────

    @Test
    fun everyKeptFrameGetsOneVectorAndDroppedFramesGetNone() {
        prepare("clip")
        VideoEmbedImages.run(db, "clip", neverCalled)

        assertEquals(2, keptIds("clip").size)
        assertEquals(keptIds("clip").sorted(), storedIds())
    }

    @Test
    fun askingWithAFramesOwnVectorReturnsThatFrameFirst() {
        val folder = prepare("clip")
        VideoEmbedImages.run(db, "clip", neverCalled)

        for ((frameId, vector) in VideoDedup.readVectors(File(folder, VideoDedup.VECTORS_FILE))) {
            val (best, score) = VideoVectors.knn(db, "image_vec", vector, 1).single()
            assertEquals(frameId, best)
            assertEquals(1f, score, 1e-6f)
        }
    }

    @Test
    fun runningTheStageAgainKeepsTheSameVectors() {
        prepare("clip")
        VideoEmbedImages.run(db, "clip", neverCalled)
        val first = storedIds()
        VideoEmbedImages.run(db, "clip", neverCalled)
        assertEquals(first, storedIds())
    }

    @Test
    fun aKeptFrameWithNoSavedVectorIsEmbeddedHere() {
        val folder = prepare("clip")
        File(folder, VideoDedup.VECTORS_FILE).delete()
        val asked = ArrayList<String>()
        VideoEmbedImages.run(db, "clip") { file -> asked.add(file.name); along(7) }

        assertEquals(listOf("000001.jpg", "000004.jpg"), asked)
        assertEquals(keptIds("clip").sorted(), storedIds())
    }

    // ── Vector storage and search ────────────────────────────────────────────────

    @Test
    fun theNearestRowsComeBackBestFirst() {
        prepare("clip")
        val (first, second) = keptIds("clip")
        VideoVectors.put(db, "image_vec", first, along(0))
        VideoVectors.put(db, "image_vec", second, FloatArray(ImageEmbedder.DIMENSIONS).also { it[0] = 0.6f; it[1] = 0.8f })

        assertEquals(listOf(first to 1f, second to 0.6f), VideoVectors.knn(db, "image_vec", along(0), 5))
        assertEquals(listOf(second), VideoVectors.knn(db, "image_vec", along(1), 1).map { it.first })
    }

    @Test
    fun aVectorOfTheWrongSizeIsRefused() {
        prepare("clip")
        assertThrows(IllegalArgumentException::class.java) { VideoVectors.put(db, "image_vec", keptIds("clip").first(), FloatArray(8)) }
    }

    @Test
    fun searchSeesRowsAddedOrRemovedSinceTheLastSearch() {
        prepare("clip")
        assertEquals(emptyList<Pair<Long, Float>>(), VideoVectors.knn(db, "image_vec", along(0), 5))

        VideoEmbedImages.run(db, "clip", neverCalled)
        assertEquals(2, VideoVectors.knn(db, "image_vec", along(0), 5).size)

        db.execSQL("DELETE FROM videos WHERE video_id = 'clip'") // the video's frames and vectors go with it
        assertEquals(emptyList<Long>(), storedIds())
        assertEquals(emptyList<Pair<Long, Float>>(), VideoVectors.knn(db, "image_vec", along(0), 5))
    }

    // ── The real models on this phone ────────────────────────────────────────────

    @Test
    fun theWholeJobStoresARealVectorForEveryKeptFrameWithTheRealModels() {
        assumeTrue("models not on this phone", ObjectDetector.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists())
        addVideo("job")
        val jobs = VideoJobs { db }
        jobs.enqueue("job")
        VideoWorker({ db }, jobs).drain()

        val (status, stage, error) = db.query("SELECT status, stage, error FROM jobs WHERE video_id = 'job'").use { it.moveToFirst(); Triple(it.getString(0), it.getString(1), it.getString(2)) }
        assertEquals("job error: $error", "done", status)
        assertEquals(VideoPipeline.STAGES.last().first, stage)
        assertEquals(keptIds("job").sorted(), storedIds())
        db.query("SELECT frame_id, embedding FROM image_vec").use { c ->
            while (c.moveToNext()) {
                val vector = VideoVectors.fromBlob(c.getBlob(1))
                assertEquals(ImageEmbedder.DIMENSIONS, vector.size)
                assertEquals(1.0, vector.sumOf { it.toDouble() * it }, 1e-3)
                assertEquals(c.getLong(0), VideoVectors.knn(db, "image_vec", vector, 1).single().first)
            }
        }
        assertTrue(storedIds().isNotEmpty())
    }
}
