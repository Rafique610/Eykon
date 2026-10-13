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
import com.eykon.memory.ml.vision.Detection
import com.eykon.memory.ml.vision.ImageEmbedder
import com.eykon.memory.ml.vision.ObjectDetector
import kotlinx.serialization.json.Json
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
 * The scene stage on a real phone. Tests named "...WithTheRealModels" need yolox_tiny.onnx and
 * mobileclip_s2_image.onnx in the phone's models folder and are skipped when they are not there.
 */
@RunWith(AndroidJUnit4::class)
class VideoSceneTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        root = File(context.cacheDir, "scene_test").apply { deleteRecursively(); mkdirs() }
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        helper = FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build())
        db = helper.writableDatabase
    }

    @After
    fun close() {
        helper.close()
        root.deleteRecursively()
    }

    private val testAssets get() = InstrumentationRegistry.getInstrumentation().context.assets
    private val modelsAreOnThePhone get() = ObjectDetector.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists()

    private fun addVideo(videoId: String, copyFrom: (File) -> Unit, durationS: Double? = null): File {
        val folder = File(root, videoId).apply { mkdirs() }
        val file = File(folder, "$videoId.mp4").also(copyFrom)
        val length = durationS ?: MediaMetadataRetriever().run {
            setDataSource(file.absolutePath)
            (extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)!!.toLong() / 1000.0).also { release() }
        }
        VideoRepository { db }.insert(Video(videoId = videoId, filePath = file.absolutePath, recordedAt = "2026-10-13T16:00:00Z", createdAt = "2026-10-13T16:00:00Z", durationS = length))
        return folder
    }

    /** test_clip_repeat.mp4 (A, B, A, B) through split, filter and a stand-in dedup: frames 1 and 4 stay kept. */
    private fun prepare(videoId: String): File {
        val folder = addVideo(videoId, { file -> testAssets.open("test_clip_repeat.mp4").use { input -> file.outputStream().use { input.copyTo(it) } } }, 4.0)
        VideoSplit.run(db, videoId)
        VideoFilter.run(db, videoId, 1)
        var next = 0
        VideoDedup.run(db, videoId) { FloatArray(8).also { it[next++ % 8] = 1f } }
        return folder
    }

    private class Record(val frameNo: Int, val objects: String, val action: String?, val place: String?, val people: Int, val caption: String, val source: String)

    private fun records(videoId: String): List<Record> =
        db.query(
            "SELECT f.frame_no, s.objects, s.action, s.place, s.people, s.caption, s.source FROM scene_records s JOIN frames f ON f.id = s.frame_id WHERE f.video_id = ? ORDER BY f.t_s",
            arrayOf(videoId),
        ).use { c ->
            buildList { while (c.moveToNext()) add(Record(c.getInt(0), c.getString(1), if (c.isNull(2)) null else c.getString(2), if (c.isNull(3)) null else c.getString(3), c.getInt(4), c.getString(5), c.getString(6))) }
        }

    private val laptopInAnOffice: Describe = { _, _ ->
        Perception(listOf(Detection("laptop", 0.8f, listOf(1f, 2f, 3f, 4f))), "typing on a laptop", "an office", 1)
    }

    // ── The stage's rules, with a stand-in for the models ───────────────────────

    @Test
    fun everyKeptFrameGetsExactlyOneRecordAndDroppedFramesGetNone() {
        prepare("clip")
        VideoScene.run(db, "clip", "A", laptopInAnOffice)

        val written = records("clip")
        assertEquals(listOf(1, 4), written.map { it.frameNo }) // the two frames dedup kept, in time order
        written.forEach {
            assertEquals("A", it.source)
            assertEquals("laptop, 1 person, in an office, typing on a laptop", it.caption)
            assertEquals("an office", it.place)
            assertEquals("typing on a laptop", it.action)
            assertEquals(1, it.people)
            val thing = Json.parseToJsonElement(it.objects).jsonArray.single().jsonObject
            assertEquals("laptop", thing["label"]!!.jsonPrimitive.content)
            assertEquals(listOf("1.0", "2.0", "3.0", "4.0"), thing["box"]!!.jsonArray.map { n -> n.jsonPrimitive.content })
        }
    }

    @Test
    fun aFrameWithNothingInItStillGetsARecord() {
        prepare("clip")
        VideoScene.run(db, "clip", "A") { _, _ -> Perception(emptyList(), null, null, 0) }

        val written = records("clip")
        assertEquals(2, written.size)
        written.forEach {
            assertEquals("nothing recognised", it.caption)
            assertEquals("[]", it.objects)
            assertEquals(null, it.place)
        }
    }

    @Test
    fun anOptionsOwnCaptionIsKept() {
        prepare("clip")
        VideoScene.run(db, "clip", "C") { _, _ -> Perception(emptyList(), null, null, 0, caption = "a desk with a red mug") }
        assertEquals(listOf("a desk with a red mug" to "C", "a desk with a red mug" to "C"), records("clip").map { it.caption to it.source })
    }

    @Test
    fun theSavedImageVectorIsHandedToTheOptionForEachFrame() {
        val folder = prepare("clip")
        val saved = VideoDedup.readVectors(File(folder, VideoDedup.VECTORS_FILE))
        val given = ArrayList<FloatArray?>()
        VideoScene.run(db, "clip", "A") { file, vector -> assertTrue(file.exists()); given.add(vector); Perception(emptyList(), null, null, 0) }

        assertEquals(2, given.size)
        assertEquals(saved.values.map { it.toList() }.toSet(), given.map { it!!.toList() }.toSet())
    }

    @Test
    fun runningTheStageAgainReplacesTheRecords() {
        prepare("clip")
        VideoScene.run(db, "clip", "A", laptopInAnOffice)
        VideoScene.run(db, "clip", "A") { _, _ -> Perception(emptyList(), null, "a street", 0) }

        assertEquals(listOf("in a street", "in a street"), records("clip").map { it.caption })
    }

    @Test
    fun deletingTheVideoRemovesItsRecords() {
        prepare("clip")
        VideoScene.run(db, "clip", "A", laptopInAnOffice)
        db.execSQL("DELETE FROM videos WHERE video_id = 'clip'")
        assertEquals(0, db.query("SELECT COUNT(*) FROM scene_records").use { it.moveToFirst(); it.getInt(0) })
    }

    // ── The real models on this phone ────────────────────────────────────────────

    @Test
    fun theWholeJobEndsWithARecordForEveryKeptFrameWithTheRealModels() {
        assumeTrue("models not on this phone", modelsAreOnThePhone)
        addVideo("job", { file -> testAssets.open("test_clip_repeat.mp4").use { input -> file.outputStream().use { input.copyTo(it) } } }, 4.0)
        val jobs = VideoJobs { db }
        jobs.enqueue("job")
        VideoWorker({ db }, jobs).drain()

        val (status, stage, error) = db.query("SELECT status, stage, error FROM jobs WHERE video_id = 'job'").use { it.moveToFirst(); Triple(it.getString(0), it.getString(1), it.getString(2)) }
        assertEquals("job error: $error", "done", status)
        assertEquals(VideoPipeline.STAGES.last().first, stage)
        val kept = db.query("SELECT frame_no FROM frames WHERE video_id = 'job' AND kept = 1 ORDER BY t_s").use { c -> buildList { while (c.moveToNext()) add(c.getInt(0)) } }
        val written = records("job")
        assertEquals(kept, written.map { it.frameNo })
        assertTrue(written.all { it.source == "A" && it.caption.isNotBlank() })
    }

    /** Not pass/fail: writes the captions of a real clip to logcat (tag EykonVideo) so a person can read them. */
    @Test
    fun captionsOfARealClipWithTheRealModels() {
        val clip = File(context.getExternalFilesDir(null), "eval_clips/" + (InstrumentationRegistry.getArguments().getString("clip") ?: "clip4.mp4"))
        assumeTrue("models or ${clip.name} not on this phone", modelsAreOnThePhone && clip.exists())
        addVideo("real", { file -> clip.copyTo(file, overwrite = true) })
        val jobs = VideoJobs { db }
        jobs.enqueue("real")
        VideoWorker({ db }, jobs).drain()

        db.query("SELECT f.t_s, s.caption, s.people, s.objects FROM scene_records s JOIN frames f ON f.id = s.frame_id WHERE f.video_id = 'real' ORDER BY f.t_s").use { c ->
            while (c.moveToNext()) Log.i("EykonVideo", "scene caption ${clip.name} %5.1f s: %s".format(c.getDouble(0), c.getString(1)))
        }
        val kept = db.query("SELECT COUNT(*) FROM frames WHERE video_id = 'real' AND kept = 1").use { it.moveToFirst(); it.getInt(0) }
        assertEquals(kept, records("real").size)
    }
}
