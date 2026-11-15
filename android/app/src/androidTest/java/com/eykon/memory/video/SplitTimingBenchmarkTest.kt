package com.eykon.memory.video

import android.content.Context
import android.media.MediaMetadataRetriever
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Where the split stage's frame time goes on a real phone clip: decoding, turning a frame into a JPEG, writing it.
 * Measurement only (not in the pass/fail suite). It decides whether checking sharpness before a frame is saved is worth building:
 * that change can only save the JPEG and write time of the frames dropped later.
 *   adb push <kit clip> /sdcard/Android/data/com.eykon.memory/files/eval_clips/kit1.mp4
 *   adb shell am instrument -w -e class com.eykon.memory.video.SplitTimingBenchmarkTest com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
 * Result in logcat, tag EykonVideo, lines starting "split timing".
 */
@RunWith(AndroidJUnit4::class)
class SplitTimingBenchmarkTest {

    @Test
    fun whereTheFrameTimeGoes() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val clip = File(context.getExternalFilesDir(null), "eval_clips/kit1.mp4")
        assumeTrue("push a kit clip to eval_clips/kit1.mp4", clip.exists())
        val durationS = MediaMetadataRetriever().run {
            try { setDataSource(clip.absolutePath); extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)!!.toDouble() / 1000 } finally { release() }
        }
        val times = VideoSplit.frameTimes(durationS)
        val dir = File(context.cacheDir, "split-timing").apply { deleteRecursively(); mkdirs() }
        try {
            repeat(3) { run ->
                dir.listFiles()?.forEach { it.delete() }
                val timing = FrameExtractor.Timing()
                val start = System.nanoTime()
                val saved = FrameExtractor.decodeInOnePass(clip.absolutePath, dir, times, VideoSplit.FRAME_MAX_SIDE, VideoSplit.JPEG_QUALITY, timing)
                val totalMs = (System.nanoTime() - start) / 1_000_000
                val convertMs = timing.convertNs / 1_000_000
                val writeMs = timing.writeNs / 1_000_000
                // one hash over every JPEG in frame order: a faster version must give the same bytes
                val digest = java.security.MessageDigest.getInstance("SHA-256")
                dir.listFiles()!!.sortedBy { it.name }.forEach { digest.update(it.readBytes()) }
                val hash = digest.digest().joinToString("") { "%02x".format(it) }.take(16)
                Log.i(
                    "EykonVideo",
                    "split timing run ${run + 1}: ${saved.size} frames of ${"%.1f".format(durationS)} s in $totalMs ms: " +
                        "decoding ${totalMs - convertMs - writeMs} ms, to JPEG $convertMs ms, write $writeMs ms, jpeg hash $hash",
                )
            }
        } finally {
            dir.deleteRecursively()
        }
    }
}
