package com.eykon.memory.video

import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import java.io.File
import kotlin.math.ceil

/**
 * Stage "split" (card EYKO-4): pull frames as JPEGs and the sound as a 16 kHz mono WAV.
 * The laptop does this with ffmpeg; the phone uses its own video and audio decoders.
 */
object VideoSplit {

    const val FPS = 3.0 // allowed 2 to 4
    const val JPEG_QUALITY = 90
    const val FRAME_MAX_SIDE = 640 // frames are shrunk to fit; the laptop keeps the full size
    const val AUDIO_RATE = 16_000
    const val AUDIO_FILE = "audio16k.wav"
    private const val TAG = "EykonVideo"

    /** Frame n (from 1) is at (n - 1) / fps seconds, like ffmpeg's fps filter. */
    fun frameTimes(durationS: Double, fps: Double = FPS): List<Double> =
        List(ceil(durationS * fps - 1e-6).toInt().coerceAtLeast(0)) { it / fps }

    fun run(db: SupportSQLiteDatabase, videoId: String) {
        val (filePath, durationS) = db.query("SELECT file_path, duration_s FROM videos WHERE video_id = ?", arrayOf(videoId)).use { cursor ->
            if (!cursor.moveToFirst()) throw IllegalStateException("video $videoId is not in the database")
            cursor.getString(0) to cursor.getDouble(1)
        }
        val folder = File(filePath).parentFile ?: throw IllegalStateException("video file has no folder")
        val framesDir = File(folder, "frames")
        val times = frameTimes(durationS)

        // Idempotent: remove what an earlier run of this stage wrote.
        db.execSQL("DELETE FROM frames WHERE video_id = ?", arrayOf(videoId))

        val startFrames = System.nanoTime()
        var method = "one pass"
        val saved = try {
            resetDir(framesDir)
            FrameExtractor.decodeInOnePass(filePath, framesDir, times, FRAME_MAX_SIDE, JPEG_QUALITY)
        } catch (e: Exception) {
            Log.w(TAG, "split $videoId: one-pass decoding failed (${e.javaClass.simpleName}: ${e.message}); reading frame by frame")
            method = "frame by frame"
            resetDir(framesDir)
            FrameExtractor.seekEachFrame(filePath, framesDir, times, FRAME_MAX_SIDE, JPEG_QUALITY)
        }
        val framesMs = (System.nanoTime() - startFrames) / 1_000_000
        if (saved.isEmpty()) throw RuntimeException("no frame could be read from the video")

        val startAudio = System.nanoTime()
        val audioSamples = AudioExtractor.toWav(filePath, File(folder, AUDIO_FILE), durationS, AUDIO_RATE)
        val audioMs = (System.nanoTime() - startAudio) / 1_000_000

        db.beginTransaction()
        try {
            saved.forEach { (frameNo, t) ->
                db.execSQL(
                    "INSERT INTO frames (video_id, frame_no, t_s, path) VALUES (?, ?, ?, ?)",
                    arrayOf(videoId, frameNo, t, "$videoId/frames/%06d.jpg".format(frameNo)),
                )
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        Log.i(TAG, "split $videoId: ${saved.size} frames in $framesMs ms ($method), audio ${"%.1f".format(audioSamples / AUDIO_RATE.toDouble())} s in $audioMs ms")
    }

    private fun resetDir(dir: File) {
        dir.deleteRecursively()
        dir.mkdirs()
    }
}
