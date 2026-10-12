package com.eykon.memory.video

import android.content.Context
import android.graphics.BitmapFactory
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.vision.ImageEmbedder
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
 * The dedup stage on a real phone. test_clip_repeat.mp4 shows picture A for 1 s, picture B for
 * 1 s, then A again and B again: the scene comes back, which only this stage can notice.
 *
 * Tests named "...WithTheRealModel" need mobileclip_s2_image.onnx in the phone's models folder
 * and are skipped when it is not there.
 */
@RunWith(AndroidJUnit4::class)
class VideoDedupTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        root = File(context.cacheDir, "dedup_test").apply { deleteRecursively(); mkdirs() }
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

    private val testAssets get() = InstrumentationRegistry.getInstrumentation().context.assets

    /** Adds the clip and runs the two stages before dedup. */
    private fun prepare(asset: String, videoId: String, durationS: Double): File {
        val folder = File(root, videoId).apply { mkdirs() }
        val file = File(folder, "$videoId.mp4")
        testAssets.open(asset).use { input -> file.outputStream().use { input.copyTo(it) } }
        VideoRepository { db }.insert(
            Video(videoId = videoId, filePath = file.absolutePath, recordedAt = "2026-10-12T16:00:00Z", createdAt = "2026-10-12T16:00:00Z", durationS = durationS),
        )
        VideoSplit.run(db, videoId)
        VideoFilter.run(db, videoId)
        return folder
    }

    private class Row(val id: Long, val frameNo: Int, val kept: Int, val reason: String?, val phash: String?)

    private fun rows(videoId: String): List<Row> =
        db.query("SELECT id, frame_no, kept, drop_reason, phash FROM frames WHERE video_id = ? ORDER BY frame_no", arrayOf(videoId)).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(Row(cursor.getLong(0), cursor.getInt(1), cursor.getInt(2), if (cursor.isNull(3)) null else cursor.getString(3), if (cursor.isNull(4)) null else cursor.getString(4)))
                }
            }
        }

    private fun kept(videoId: String) = rows(videoId).filter { it.kept == 1 }.map { it.frameNo }

    /** A stand-in for the model: every frame gets its own direction, so no two frames "show the same thing". */
    private fun allDifferent(): (File) -> FloatArray {
        var next = 0
        return { FloatArray(8).also { it[next++ % 8] = 1f } }
    }

    private val modelIsOnThePhone get() = ImageEmbedder.modelFile(context).exists()

    // ── The stage's rules, with a stand-in for the model ────────────────────────

    @Test
    fun aSceneThatComesBackIsKeptOnlyOnce() {
        prepare("test_clip_repeat.mp4", "repeat", 4.0)
        // The filters only compare with the frame before, so they keep each change: A, B, A, B.
        assertEquals(listOf(1, 4, 7, 10), kept("repeat"))

        VideoDedup.run(db, "repeat", allDifferent())

        val after = rows("repeat")
        assertEquals(listOf(1, 4), kept("repeat"))
        assertEquals("duplicate of frame 1", after.first { it.frameNo == 7 }.reason)
        assertEquals("duplicate of frame 4", after.first { it.frameNo == 10 }.reason)
        // every frame this stage looked at has its hash stored; frames the filters dropped do not
        listOf(1, 4, 7, 10).forEach { n -> assertEquals(16, after.first { it.frameNo == n }.phash!!.length) }
        assertTrue(after.filter { it.reason == "still" }.all { it.phash == null })
        assertEquals(after.first { it.frameNo == 1 }.phash, after.first { it.frameNo == 7 }.phash)
    }

    @Test
    fun framesThatLookDifferentButShowTheSameThingAreCaughtByTheSecondLayer() {
        prepare("test_clip_repeat.mp4", "repeat", 4.0)
        var calls = 0
        val sameThing: (File) -> FloatArray = { calls++; floatArrayOf(1f, 0f) } // the "model" says: all the same

        VideoDedup.run(db, "repeat", sameThing)

        assertEquals(listOf(1), kept("repeat"))
        assertEquals("duplicate of frame 1", rows("repeat").first { it.frameNo == 4 }.reason)
        // Only frames that pass the hash layer reach the model: A, B, and the second B.
        // The second A matches the first A's hash and never gets there. The second B does,
        // because the first B was dropped and so is not among the unique frames to compare with.
        assertEquals(3, calls)
    }

    @Test
    fun theUniqueFramesVectorsAreSavedForTheNextStage() {
        val folder = prepare("test_clip_repeat.mp4", "repeat", 4.0)
        VideoDedup.run(db, "repeat", allDifferent())

        val saved = VideoDedup.readVectors(File(folder, VideoDedup.VECTORS_FILE))
        val uniqueIds = rows("repeat").filter { it.kept == 1 }.map { it.id }.toSet()
        assertEquals(uniqueIds, saved.keys)
        assertTrue(saved.values.all { it.size == 8 && it.sum() == 1f })
    }

    @Test
    fun runningTheStageAgainGivesTheSameResult() {
        prepare("test_clip_repeat.mp4", "repeat", 4.0)
        VideoDedup.run(db, "repeat", allDifferent())
        val first = rows("repeat").map { Triple(it.frameNo, it.kept, it.reason) }

        VideoDedup.run(db, "repeat", allDifferent())

        assertEquals(first, rows("repeat").map { Triple(it.frameNo, it.kept, it.reason) })
    }

    @Test
    fun everyDuplicatePointsAtAnEarlierKeptFrame() {
        prepare("test_clip.mp4", "moving", 10.0)
        val keptByFilters = kept("moving").size
        VideoDedup.run(db, "moving", allDifferent())

        val after = rows("moving")
        assertTrue(after.count { it.kept == 1 } in 1..keptByFilters)
        after.filter { it.reason?.startsWith("duplicate") == true }.forEach { row ->
            val of = row.reason!!.removePrefix("duplicate of frame ").toInt()
            assertTrue("frame ${row.frameNo}", of < row.frameNo && after.first { it.frameNo == of }.kept == 1)
        }
    }

    // ── The real model on this phone ─────────────────────────────────────────────

    @Test
    fun thePhoneGivesTheSameVectorsAsTheLaptopWithTheRealModel() {
        assumeTrue("model not on this phone", modelIsOnThePhone)
        val golden = Json.parseToJsonElement(testAssets.open("clip_golden.json").bufferedReader().readText()).jsonObject
        for ((name, expected) in golden["vectors"]!!.jsonObject) {
            val laptop = expected.jsonArray.map { it.jsonPrimitive.float }
            val picture = testAssets.open("filters/$name.png").use(BitmapFactory::decodeStream)
            val phone = ImageEmbedder.embed(context, picture)

            assertEquals(ImageEmbedder.DIMENSIONS, phone.size)
            assertEquals("$name length", 1.0, phone.sumOf { it.toDouble() * it }, 1e-3)
            val cosine = phone.indices.sumOf { phone[it].toDouble() * laptop[it] }
            android.util.Log.i("EykonVideo", "clip parity $name: cosine with the laptop %.4f".format(cosine))
            assertTrue("$name: phone and laptop agree only $cosine", cosine > 0.98)
        }
        // Time per picture once the model is loaded (the loop above loaded it).
        val picture = testAssets.open("filters/sharp.png").use(BitmapFactory::decodeStream)
        val times = List(10) { System.nanoTime().let { start -> ImageEmbedder.embed(context, picture); (System.nanoTime() - start) / 1_000_000 } }.sorted()
        android.util.Log.i("EykonVideo", "clip speed: median ${times[5]} ms, worst ${times.last()} ms per picture over 10 runs")
    }

    @Test
    fun theWholeJobRunsAllThreeStagesWithTheRealModel() {
        assumeTrue("model not on this phone", modelIsOnThePhone)
        val folder = File(root, "job").apply { mkdirs() }
        val file = File(folder, "job.mp4")
        testAssets.open("test_clip_repeat.mp4").use { input -> file.outputStream().use { input.copyTo(it) } }
        VideoRepository { db }.insert(
            Video(videoId = "job", filePath = file.absolutePath, recordedAt = "2026-10-12T16:00:00Z", createdAt = "2026-10-12T16:00:00Z", durationS = 4.0),
        )
        val jobs = VideoJobs { db }
        jobs.enqueue("job")
        VideoWorker({ db }, jobs).drain()

        val (status, stage, error) = db.query("SELECT status, stage, error FROM jobs WHERE video_id = 'job'").use { it.moveToFirst(); Triple(it.getString(0), it.getString(1), it.getString(2)) }
        assertEquals("job error: $error", "done", status)
        assertEquals(VideoPipeline.STAGES.last().first, stage)
        // A and B are different pictures (the laptop measured cosine 0.72), so both stay
        assertEquals(listOf(1, 4), kept("job"))
        assertEquals(2, VideoDedup.readVectors(File(folder, VideoDedup.VECTORS_FILE)).values.count { it.size == ImageEmbedder.DIMENSIONS })
    }
}
