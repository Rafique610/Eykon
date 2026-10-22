package com.eykon.memory.video

import android.content.Context
import android.graphics.BitmapFactory
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * The split stage on a real phone, with two 10 s clips made by ffmpeg (640x360, 30 fps):
 * test_clip.mp4 has a 440 Hz tone in stereo at 48 kHz, test_clip_silent.mp4 has no sound track.
 */
@RunWith(AndroidJUnit4::class)
class VideoSplitTest {

    private lateinit var helper: SupportSQLiteOpenHelper
    private lateinit var db: SupportSQLiteDatabase
    private lateinit var root: File

    @Before
    fun open() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        root = File(context.cacheDir, "split_test").apply { deleteRecursively(); mkdirs() }
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

    /** Copies a test clip into its own video folder and adds its videos row, as the picker does. */
    private fun addVideo(asset: String, videoId: String): File {
        val folder = File(root, videoId).apply { mkdirs() }
        val file = File(folder, "$videoId.mp4")
        InstrumentationRegistry.getInstrumentation().context.assets.open(asset).use { input ->
            file.outputStream().use { input.copyTo(it) }
        }
        VideoRepository { db }.insert(
            Video(videoId = videoId, filePath = file.absolutePath, recordedAt = "2026-10-12T16:00:00Z", createdAt = "2026-10-12T16:00:00Z", durationS = 10.0),
        )
        return folder
    }

    private fun frameRows(videoId: String): List<Triple<Int, Double, String>> =
        db.query("SELECT frame_no, t_s, path FROM frames WHERE video_id = ? ORDER BY frame_no", arrayOf(videoId)).use { cursor ->
            buildList { while (cursor.moveToNext()) add(Triple(cursor.getInt(0), cursor.getDouble(1), cursor.getString(2))) }
        }

    private class Wav(val rate: Int, val channels: Int, val bits: Int, val samples: ShortArray)

    private fun readWav(file: File): Wav {
        val bytes = file.readBytes()
        val header = ByteBuffer.wrap(bytes, 0, 44).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals("RIFF", String(bytes, 0, 4))
        assertEquals("WAVE", String(bytes, 8, 4))
        val dataLength = header.getInt(40)
        assertEquals(bytes.size - 44, dataLength)
        val data = ByteBuffer.wrap(bytes, 44, dataLength).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        return Wav(header.getInt(24), header.getShort(22).toInt(), header.getShort(34).toInt(), ShortArray(data.remaining()).also { data.get(it) })
    }

    @Test
    fun aTenSecondClipGivesThirtyFramesAndATenSecondWav() {
        val folder = addVideo("test_clip.mp4", "v1")
        VideoSplit.run(db, "v1")

        val rows = frameRows("v1")
        assertEquals(30, rows.size)
        assertEquals((1..30).toList(), rows.map { it.first })
        assertEquals(0.0, rows.first().second, 1e-9)
        assertEquals(9.667, rows.last().second, 0.01)
        rows.forEach { (_, _, path) ->
            val image = BitmapFactory.decodeFile(File(root, path).absolutePath)
            assertEquals(640, image.width)
            assertEquals(360, image.height)
        }

        val wav = readWav(File(folder, VideoSplit.AUDIO_FILE))
        assertEquals(16_000, wav.rate)
        assertEquals(1, wav.channels)
        assertEquals(16, wav.bits)
        val seconds = wav.samples.size / 16_000.0
        assertTrue("wav is $seconds s", abs(seconds - 10.0) < 0.2)

        // The tone survived decoding, mixing to mono and resampling: right pitch, clearly not silence.
        val crossings = (1 until wav.samples.size).count { wav.samples[it - 1] < 0 && wav.samples[it] >= 0 }
        assertEquals(440.0, crossings / seconds, 10.0)
        val rms = sqrt(wav.samples.sumOf { it.toDouble() * it } / wav.samples.size) / 32768
        assertTrue("rms is $rms", rms > 0.03 && rms < 0.2)
    }

    @Test
    fun runningTheStageTwiceGivesTheSameRows() {
        val folder = addVideo("test_clip.mp4", "v1")
        VideoSplit.run(db, "v1")
        val first = frameRows("v1")
        VideoSplit.run(db, "v1")

        assertEquals(first, frameRows("v1"))
        assertEquals(30, File(folder, "frames").listFiles()!!.size)
    }

    @Test
    fun aClipWithNoSoundStillGetsASilentWav() {
        val folder = addVideo("test_clip_silent.mp4", "quiet")
        VideoSplit.run(db, "quiet")

        assertEquals(30, frameRows("quiet").size)
        val wav = readWav(File(folder, VideoSplit.AUDIO_FILE))
        assertEquals(16_000, wav.rate)
        assertEquals(160_000, wav.samples.size)
        assertTrue(wav.samples.all { it == 0.toShort() })
    }

    @Test
    fun theWholeJobRunsThroughTheWorker() {
        addVideo("test_clip.mp4", "v1")
        val jobs = VideoJobs { db }
        jobs.enqueue("v1")
        VideoWorker({ db }, jobs, listOf("split" to VideoSplit::run)).drain() // this card's stage only: needs no model

        val job = db.query("SELECT status, stage, error FROM jobs WHERE video_id = 'v1'").use { it.moveToFirst(); Triple(it.getString(0), it.getString(1), it.getString(2)) }
        assertEquals("done", job.first)
        assertEquals("split", job.second)
        assertEquals(30, frameRows("v1").size)
    }
}
