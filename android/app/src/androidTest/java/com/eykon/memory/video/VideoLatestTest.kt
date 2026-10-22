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
import kotlinx.serialization.json.jsonArray
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * The latest stage on a real phone. In the rule tests a stand-in replaces the model: an
 * object's "look" is a number written as the left edge of its box, and two crops are the same
 * object exactly when that number is the same.
 */
@RunWith(AndroidJUnit4::class)
class VideoLatestTest {

    private lateinit var context: Context
    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        context = ApplicationProvider.getApplicationContext()
        root = File(context.cacheDir, "latest_test").apply { deleteRecursively(); mkdirs() }
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

    /** One thing in a frame: its name and its look (the number the stand-in turns into a direction). */
    private class Thing(val label: String, val look: Int, val width: Int = 100)

    /** A video recorded at [recordedAt] with one frame per entry: seconds in, place, the things seen. */
    private fun video(id: String, recordedAt: String, vararg frames: Triple<Double, String?, List<Thing>>) {
        VideoRepository { db }.insert(Video(videoId = id, filePath = File(root, "$id/$id.mp4").absolutePath, recordedAt = recordedAt, createdAt = recordedAt, durationS = 60.0))
        frames.forEachIndexed { n, (tS, place, things) ->
            db.execSQL("INSERT INTO frames (video_id, frame_no, t_s, path) VALUES (?, ?, ?, ?)", arrayOf(id, n + 1, tS, "$id/frames/%06d.jpg".format(n + 1)))
            val frameId = db.query("SELECT last_insert_rowid()").use { it.moveToFirst(); it.getLong(0) }
            val objects = things.joinToString(",", "[", "]") { """{"label":"${it.label}","conf":0.9,"box":[${it.look}.0,0.0,${it.look + it.width}.0,100.0]}""" }
            db.execSQL("INSERT INTO scene_records (frame_id, objects, place, caption, source) VALUES (?, ?, ?, 'caption', 'A')", arrayOf(frameId, objects, place))
        }
    }

    private val byLook: EmbedCrop = { _, box -> if (box[2] - box[0] < VideoLatest.MIN_BOX_SIDE) null else FloatArray(ImageEmbedder.DIMENSIONS).also { it[box[0].toInt()] = 1f } }

    private fun process(vararg ids: String) = ids.forEach { VideoLatest.run(db, it, 0.87f, byLook) }

    private class Sighting(val id: Long, val label: String, val videoId: String, val seenAt: String, val place: String?, val isLatest: Boolean, val supersededBy: Long?)

    private fun sightings(label: String? = null) =
        db.query("SELECT id, label, video_id, seen_at, place, is_latest, superseded_by FROM object_sightings ORDER BY seen_at, id").use { c ->
            buildList { while (c.moveToNext()) add(Sighting(c.getLong(0), c.getString(1), c.getString(2), c.getString(3), if (c.isNull(4)) null else c.getString(4), c.getInt(5) == 1, if (c.isNull(6)) null else c.getLong(6))) }
        }.filter { label == null || it.label == label }

    /** What "where is it now" reads: label, video and place of every latest sighting, in a fixed order. */
    private fun latest() = sightings().filter { it.isLatest }.map { Triple(it.label, it.videoId, it.place) }.sortedBy { it.toString() }

    private val keys = Thing("keys", 7)

    // ── The card's four checks ───────────────────────────────────────────────────

    @Test
    fun theSameKeysInTheSamePlaceOnTwoDaysLeaveOneLatestSightingFromTheNewerClip() {
        video("monday", "2026-10-05T08:00:00Z", Triple(2.0, "a hallway", listOf(keys)))
        video("tuesday", "2026-10-06T08:00:00Z", Triple(5.0, "a hallway", listOf(keys)))
        process("monday", "tuesday")

        val (old, new) = sightings("keys")
        assertEquals(listOf(Triple("keys", "tuesday", "a hallway")), latest())
        assertEquals("2026-10-06T08:00:05.000Z", new.seenAt) // recording time plus the seconds into the video
        assertEquals(false, old.isLatest)
        assertEquals(new.id, old.supersededBy) // the older one is kept and says what replaced it
        assertEquals(null, new.supersededBy)
    }

    @Test
    fun theSameKeysInAnotherRoomAreStillOneLatestSightingAndItSaysTheNewRoom() {
        video("monday", "2026-10-05T08:00:00Z", Triple(2.0, "a hallway", listOf(keys)))
        video("tuesday", "2026-10-06T08:00:00Z", Triple(5.0, "a kitchen", listOf(keys)))
        process("monday", "tuesday")

        assertEquals(listOf(Triple("keys", "tuesday", "a kitchen")), latest())
        assertEquals(2, sightings("keys").size)
    }

    @Test
    fun aThirdClipWithOtherThingsAddsItsOwnLatestSightingsAndLeavesTheKeysAlone() {
        video("monday", "2026-10-05T08:00:00Z", Triple(2.0, "a hallway", listOf(keys)))
        video("tuesday", "2026-10-06T08:00:00Z", Triple(5.0, "a kitchen", listOf(keys)))
        // a laptop, and a second set of keys that looks different
        video("wednesday", "2026-10-07T08:00:00Z", Triple(1.0, "an office", listOf(Thing("laptop", 3), Thing("keys", 9))))
        process("monday", "tuesday", "wednesday")

        assertEquals(
            listOf(Triple("keys", "tuesday", "a kitchen"), Triple("keys", "wednesday", "an office"), Triple("laptop", "wednesday", "an office")),
            latest(),
        )
    }

    @Test
    fun processingTheClipsInTheWrongOrderGivesTheSameResult() {
        video("monday", "2026-10-05T08:00:00Z", Triple(2.0, "a hallway", listOf(keys)))
        video("tuesday", "2026-10-06T08:00:00Z", Triple(5.0, "a kitchen", listOf(keys)))
        video("wednesday", "2026-10-07T08:00:00Z", Triple(1.0, "an office", listOf(Thing("laptop", 3), Thing("keys", 9))))
        process("wednesday", "tuesday", "monday")

        assertEquals(
            listOf(Triple("keys", "tuesday", "a kitchen"), Triple("keys", "wednesday", "an office"), Triple("laptop", "wednesday", "an office")),
            latest(),
        )
        // the older video did not replace the newer sighting: it is the one that was replaced
        val monday = sightings("keys").single { it.videoId == "monday" }
        assertEquals(sightings("keys").single { it.videoId == "tuesday" }.id, monday.supersededBy)
    }

    // ── Other rules ──────────────────────────────────────────────────────────────

    @Test
    fun runningTheStageAgainOnAClipChangesNothing() {
        video("monday", "2026-10-05T08:00:00Z", Triple(2.0, "a hallway", listOf(keys)))
        video("tuesday", "2026-10-06T08:00:00Z", Triple(5.0, "a kitchen", listOf(keys)))
        process("monday", "tuesday")
        val before = latest()
        process("monday", "tuesday", "monday")

        assertEquals(before, latest())
        assertEquals(2, sightings().size)
        val (old, new) = sightings("keys")
        assertEquals(new.id, old.supersededBy)
    }

    @Test
    fun whenTheNewerSightingGoesAwayTheOlderOneIsTheLatestAgain() {
        video("monday", "2026-10-05T08:00:00Z", Triple(2.0, "a hallway", listOf(keys)))
        video("tuesday", "2026-10-06T08:00:00Z", Triple(5.0, "a kitchen", listOf(keys)))
        process("monday", "tuesday")
        db.execSQL("UPDATE scene_records SET objects = '[]' WHERE frame_id IN (SELECT id FROM frames WHERE video_id = 'tuesday')")
        process("tuesday")

        val only = sightings("keys").single()
        assertEquals(Triple("monday", true, null as Long?), Triple(only.videoId, only.isLatest, only.supersededBy))
    }

    @Test
    fun withinOneVideoALaterFrameReplacesAnEarlierOneAndHistoryIsKept() {
        video("walk", "2026-10-05T08:00:00Z", Triple(1.0, "a hallway", listOf(keys)), Triple(9.0, "a kitchen", listOf(keys)), Triple(20.0, "a bedroom", listOf(keys)))
        process("walk")

        assertEquals(listOf(Triple("keys", "walk", "a bedroom")), latest())
        assertEquals(listOf("a hallway", "a kitchen", "a bedroom"), sightings("keys").map { it.place })
    }

    @Test
    fun aSightingAThirdOfASecondLaterIsTheNewerOne() {
        // 4.0 s and 4.333 s: as plain text "...:04.333Z" would sort before "...:04Z", so the stored time always has decimals
        video("walk", "2026-10-05T08:00:00Z", Triple(4.0, "a hallway", listOf(keys)), Triple(4.333, "a kitchen", listOf(keys)))
        process("walk")

        assertEquals(listOf("2026-10-05T08:00:04.000Z", "2026-10-05T08:00:04.333Z"), sightings("keys").map { it.seenAt })
        assertEquals(listOf(Triple("keys", "walk", "a kitchen")), latest())
    }

    @Test
    fun twoThingsThatLookTheSameInOneFrameBothStayLatest() {
        video("room", "2026-10-05T08:00:00Z", Triple(1.0, "a classroom", listOf(Thing("chair", 4), Thing("chair", 4))))
        process("room")
        assertEquals(2, sightings("chair").count { it.isLatest })
    }

    @Test
    fun thingsWithDifferentNamesAreNeverTheSameObjectEvenWhenTheyLookAlike() {
        video("monday", "2026-10-05T08:00:00Z", Triple(2.0, null, listOf(Thing("tv", 5))))
        video("tuesday", "2026-10-06T08:00:00Z", Triple(2.0, null, listOf(Thing("laptop", 5))))
        process("monday", "tuesday")
        assertEquals(listOf(Triple("laptop", "tuesday", null), Triple("tv", "monday", null)), latest())
    }

    @Test
    fun aBoxTooSmallToJudgeGivesNoSighting() {
        video("room", "2026-10-05T08:00:00Z", Triple(1.0, null, listOf(Thing("cell phone", 2, width = 10), keys)))
        process("room")
        assertEquals(listOf("keys"), sightings().map { it.label })
    }

    // ── The real models on this phone ────────────────────────────────────────────

    /**
     * Not pass/fail, and the one test here that touches the app's own database: it runs the stage
     * again for every video stored in the app (the stage only rewrites its own sightings) and
     * writes what is now "latest" to logcat (tag EykonVideo). Run it by name when wanted.
     */
    @Test
    fun rerunTheStageOverTheAppsOwnVideosWithTheRealModel() {
        assumeTrue("run by name with -e rerun yes", InstrumentationRegistry.getArguments().getString("rerun") == "yes")
        assumeTrue("image model not on this phone", ImageEmbedder.modelFile(context).exists())
        val appDb = com.eykon.memory.MemoryApp.instance.database.openHelper.writableDatabase
        val ids = appDb.query("SELECT j.video_id FROM jobs j JOIN videos v ON v.video_id = j.video_id WHERE j.status = 'done' ORDER BY v.created_at").use { c -> buildList { while (c.moveToNext()) add(c.getString(0)) } }
        ids.forEach { VideoLatest.run(appDb, it) }
        appDb.query("SELECT label, substr(video_id, 1, 8), seen_at, place, is_latest FROM object_sightings ORDER BY label, seen_at, id").use { c ->
            while (c.moveToNext()) Log.i("EykonVideo", "app sighting ${c.getString(0)} | ${c.getString(1)} | ${c.getString(2)} | ${if (c.isNull(3)) "-" else c.getString(3)} | ${if (c.getInt(4) == 1) "LATEST" else "replaced"}")
        }
    }

    @Test
    fun theWholeJobLeavesASightingForEveryObjectItDescribedWithTheRealModels() {
        val clip = File(context.getExternalFilesDir(null), "eval_clips/clip3.mp4")
        assumeTrue(
            "models or clip3 not on this phone",
            clip.exists() && ObjectDetector.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists() && BgeEmbedder.modelFile(context).exists(),
        )
        val folder = File(root, "real").apply { mkdirs() }
        val copy = File(folder, "real.mp4").also { clip.copyTo(it, overwrite = true) }
        val length = android.media.MediaMetadataRetriever().run { setDataSource(copy.absolutePath); (extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_DURATION)!!.toLong() / 1000.0).also { release() } }
        VideoRepository { db }.insert(Video(videoId = "real", filePath = copy.absolutePath, recordedAt = "2026-10-13T18:00:00Z", createdAt = "2026-10-13T18:00:00Z", durationS = length))
        val jobs = VideoJobs { db }
        jobs.enqueue("real")
        VideoWorker({ db }, jobs).drain()

        val (status, stage, error) = db.query("SELECT status, stage, error FROM jobs WHERE video_id = 'real'").use { it.moveToFirst(); Triple(it.getString(0), it.getString(1), it.getString(2)) }
        assertEquals("job error: $error", "done", status)
        assertEquals(VideoPipeline.STAGES.last().first, stage)
        val described = db.query("SELECT objects FROM scene_records").use { c -> var n = 0; while (c.moveToNext()) n += Json.parseToJsonElement(c.getString(0)).jsonArray.size; n }
        val all = sightings()
        Log.i("EykonVideo", "latest check clip3: $described objects described, ${all.size} sightings, latest: " + all.filter { it.isLatest }.joinToString { "${it.label} at ${it.seenAt.substring(17, 19)} s (${it.place})" })
        assertTrue(all.size <= described && all.isNotEmpty())
        db.query("SELECT embedding FROM object_sightings").use { c -> while (c.moveToNext()) assertEquals(ImageEmbedder.DIMENSIONS, VideoVectors.fromBlob(c.getBlob(0)).size) }
        assertTrue(all.all { it.isLatest || it.supersededBy != null })
    }
}
