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
import com.eykon.memory.ml.embedder.BgeEmbedder
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
 * The link stage on a real phone. Every test works on its own throw-away database, never the
 * app's; data is broken on purpose only there.
 */
@RunWith(AndroidJUnit4::class)
class VideoLinkTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        root = File(context.cacheDir, "link_test").apply { deleteRecursively(); mkdirs() }
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

    private fun addVideo(videoId: String, copy: (File) -> Unit, durationS: Double? = null) {
        val folder = File(root, videoId).apply { mkdirs() }
        val file = File(folder, "$videoId.mp4").also(copy)
        val length = durationS ?: MediaMetadataRetriever().run { setDataSource(file.absolutePath); (extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)!!.toLong() / 1000.0).also { release() } }
        VideoRepository { db }.insert(Video(videoId = videoId, filePath = file.absolutePath, recordedAt = "2026-10-13T18:00:00Z", createdAt = "2026-10-13T18:00:00Z", durationS = length))
    }

    /** The test clip through every stage before link, with stand-ins for the models: two kept frames, two captions. */
    private fun prepare(videoId: String) {
        addVideo(videoId, { file -> testAssets.open("test_clip_repeat.mp4").use { input -> file.outputStream().use { input.copyTo(it) } } }, 4.0)
        VideoSplit.run(db, videoId)
        VideoFilter.run(db, videoId, 1)
        var next = 0
        VideoDedup.run(db, videoId) { FloatArray(ImageEmbedder.DIMENSIONS).also { it[next++] = 1f } }
        VideoScene.run(db, videoId, "A") { f, _ -> Perception(emptyList(), null, null, 0, caption = "caption of ${f.name}") }
        VideoEmbedImages.run(db, videoId) { throw AssertionError("vectors are saved") }
        VideoEmbedTexts.run(db, videoId) { FloatArray(BgeEmbedder.DIMENSIONS).also { it[0] = 1f } }
    }

    private fun firstKeptFrame(videoId: String) =
        db.query("SELECT id FROM frames WHERE video_id = ? AND kept = 1 ORDER BY t_s LIMIT 1", arrayOf(videoId)).use { it.moveToFirst(); it.getLong(0) }

    @Test
    fun aVideoWhoseRowsAllHangTogetherPasses() {
        prepare("clip")
        assertEquals(emptyList<String>(), VideoLink.problems(db, "clip"))
        VideoLink.run(db, "clip") // does not throw
    }

    @Test
    fun aMissingImageVectorIsReportedAndTheStageFails() {
        prepare("clip")
        db.execSQL("DELETE FROM image_vec WHERE frame_id = ?", arrayOf(firstKeptFrame("clip")))

        assertEquals(listOf("1 kept frames without an image vector"), VideoLink.problems(db, "clip"))
        val failure = assertThrows(IllegalStateException::class.java) { VideoLink.run(db, "clip") }
        assertEquals("1 kept frames without an image vector", failure.message)
    }

    @Test
    fun everyKindOfGapIsNamedWithItsCount() {
        prepare("clip")
        val frame = firstKeptFrame("clip")
        db.execSQL("DELETE FROM text_vec")
        db.execSQL("DELETE FROM scene_records WHERE frame_id = ?", arrayOf(frame))
        db.execSQL("UPDATE frames SET phash = NULL WHERE id = ?", arrayOf(frame))
        db.execSQL("UPDATE frames SET t_s = 99 WHERE id = ?", arrayOf(frame))
        db.execSQL("INSERT INTO audio_windows (video_id, start_s, end_s) VALUES ('clip', 0, 2)")
        db.execSQL("INSERT INTO transcript_chunks (video_id, start_s, end_s, text) VALUES ('clip', 3, 60, 'said after the video ended')")

        assertEquals(
            listOf(
                "1 kept frames without a picture hash",
                "1 kept frames without a scene record",
                "2 texts without a text vector",
                "1 sound windows without a sound vector",
                "1 frames timed outside the video",
                "1 transcript chunks timed outside the video",
            ),
            VideoLink.problems(db, "clip"),
        )
    }

    @Test
    fun droppedFramesAreNotExpectedToHaveAnything() {
        prepare("clip")
        val dropped = db.query("SELECT COUNT(*) FROM frames WHERE video_id = 'clip' AND kept = 0").use { it.moveToFirst(); it.getInt(0) }
        assertTrue(dropped > 0)
        assertEquals(emptyList<String>(), VideoLink.problems(db, "clip"))
    }

    @Test
    fun aRecordingTimeThatCannotBeReadIsAProblem() {
        prepare("clip")
        db.execSQL("UPDATE videos SET recorded_at = 'yesterday' WHERE video_id = 'clip'")
        assertEquals(listOf("the video has no usable recording time (\"yesterday\")"), VideoLink.problems(db, "clip"))
    }

    @Test
    fun aFailingCheckFailsTheJobAndTheReasonIsStoredForThePerson() {
        prepare("clip")
        db.execSQL("DELETE FROM image_vec WHERE frame_id = ?", arrayOf(firstKeptFrame("clip")))
        val jobs = VideoJobs { db }
        jobs.enqueue("clip")
        VideoWorker({ db }, jobs, listOf("link" to VideoLink::run)).drain()

        val (status, error) = db.query("SELECT status, error FROM jobs WHERE video_id = 'clip'").use { it.moveToFirst(); it.getString(0) to it.getString(1) }
        assertEquals("failed", status)
        assertEquals("IllegalStateException: 1 kept frames without an image vector", error)
        // the check did not repair anything
        assertEquals(1, db.query("SELECT COUNT(*) FROM image_vec").use { it.moveToFirst(); it.getInt(0) })
    }

    /** Three real clips through the whole job with the real models: each must end with nothing to report. */
    @Test
    fun threeRealClipsPassWithTheRealModels() {
        val clips = listOf("clip2.mp4", "clip3.mp4", "clip5.mp4").map { File(context.getExternalFilesDir(null), "eval_clips/$it") }
        assumeTrue(
            "models or clips not on this phone",
            clips.all { it.exists() } && ObjectDetector.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists() && BgeEmbedder.modelFile(context).exists(),
        )
        val jobs = VideoJobs { db }
        for (clip in clips) {
            val id = clip.nameWithoutExtension
            addVideo(id, { file -> clip.copyTo(file, overwrite = true) })
            jobs.enqueue(id)
        }
        VideoWorker({ db }, jobs).drain()

        for (clip in clips) {
            val id = clip.nameWithoutExtension
            val (status, stage, error) = db.query("SELECT status, stage, error FROM jobs WHERE video_id = ?", arrayOf(id)).use { it.moveToFirst(); Triple(it.getString(0), it.getString(1), it.getString(2)) }
            val kept = db.query("SELECT COUNT(*) FROM frames WHERE video_id = ? AND kept = 1", arrayOf(id)).use { it.moveToFirst(); it.getInt(0) }
            Log.i("EykonVideo", "link check $id: job $status at stage $stage, $kept kept frames, problems ${VideoLink.problems(db, id)}")
            assertEquals("$id job error: $error", "done", status)
            assertEquals(VideoPipeline.STAGES.last().first, stage)
            assertEquals(emptyList<String>(), VideoLink.problems(db, id))
        }
    }
}
