package com.eykon.memory.video

import android.graphics.BitmapFactory
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.vision.Detection
import com.eykon.memory.ml.vision.OwlDetector
import java.io.File
import kotlin.math.max
import kotlin.math.roundToInt

/** Finds the user's own small things in one frame file. */
typealias FindOwn = (File) -> List<Detection>

/**
 * Stage "small_objects" (card EYKO-32): OWLv2 looks for the user's own small things ("keys",
 * "earbuds") in one kept frame out of three: the frames whose saved MobileCLIP vector is most like
 * "a photo of keys" or "a photo of earbuds". What it finds joins that frame's scene record and its
 * caption is written again. Measured on the Pixel: with D-FINE in the scene step, 50 of 87 own things
 * against 37 without this stage, no extra false alarms, about 59 s more for a 75 s clip
 * (docs/results/2026-10-14-detectors-open-vocabulary.md, "The mix on the Pixel").
 */
object VideoSmallObjects {

    /** OWLv2 sees one kept frame in [SHARE], at least one. */
    const val SHARE = 3
    private const val TAG = "EykonVideo"

    fun run(db: SupportSQLiteDatabase, videoId: String) {
        val context = MemoryApp.instance
        try {
            run(db, videoId, OwlDetector.pickVectors(context)) { file ->
                val picture = BitmapFactory.decodeFile(file.absolutePath) ?: throw IllegalStateException("picture ${file.name} cannot be read")
                try { OwlDetector.detect(context, picture) } finally { picture.recycle() }
            }
        } finally {
            OwlDetector.close()
        }
    }

    private class Kept(val id: Long, val path: String, val objects: String, val people: Int, val place: String?, val action: String?)

    /** [pick] are the phrase vectors that choose frames; [findOwn] is OWLv2, tests pass their own. */
    fun run(db: SupportSQLiteDatabase, videoId: String, pick: List<FloatArray>, findOwn: FindOwn) {
        val videoFolder = db.query("SELECT file_path FROM videos WHERE video_id = ?", arrayOf(videoId)).use { cursor ->
            if (!cursor.moveToFirst()) throw IllegalStateException("video $videoId is not in the database")
            File(cursor.getString(0)).parentFile ?: throw IllegalStateException("video file has no folder")
        }
        val videosDir = videoFolder.parentFile ?: throw IllegalStateException("video folder has no parent")
        val kept = db.query(
            "SELECT f.id, f.path, s.objects, s.people, s.place, s.action FROM frames f JOIN scene_records s ON s.frame_id = f.id " +
                "WHERE f.video_id = ? AND f.kept = 1 ORDER BY f.t_s",
            arrayOf(videoId),
        ).use { c -> buildList { while (c.moveToNext()) add(Kept(c.getLong(0), c.getString(1), c.getString(2), c.getInt(3), c.getStringOrNull(4), c.getStringOrNull(5))) } }
        val saved = VideoDedup.readVectors(File(videoFolder, VideoDedup.VECTORS_FILE))
        val chosen = picked(kept.map { it.id }, saved, pick)

        val start = System.nanoTime()
        val found = kept.filter { it.id in chosen }.associate { it.id to findOwn(File(videosDir, it.path)) }
        val ms = (System.nanoTime() - start) / 1_000_000

        db.beginTransaction()
        try {
            for (frame in kept) {
                // Idempotent: OWLv2's finds from an earlier run go first, then this run's are added
                val objects = VideoScene.objectsFrom(frame.objects).filter { it.source != "owl" } + found[frame.id].orEmpty()
                val perception = Perception(objects, frame.action, frame.place, frame.people)
                db.execSQL(
                    "UPDATE scene_records SET objects = ?, caption = ? WHERE frame_id = ?",
                    arrayOf(VideoScene.objectsJson(perception), VideoScene.buildCaption(perception), frame.id),
                )
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        Log.i(TAG, "small_objects $videoId: OWLv2 on ${chosen.size} of ${kept.size} frames, ${found.values.sumOf { it.size }} found, in $ms ms")
    }

    /** The [SHARE] share of [frames] whose vector is most like any [pick] vector; frames without a vector come last. */
    internal fun picked(frames: List<Long>, vectors: Map<Long, FloatArray>, pick: List<FloatArray>): Set<Long> {
        if (frames.isEmpty()) return emptySet()
        val count = max(1, (frames.size / SHARE.toDouble()).roundToInt())
        fun likeness(id: Long): Float = vectors[id]?.let { v -> pick.maxOf { p -> v.indices.sumOf { (v[it] * p[it]).toDouble() }.toFloat() } } ?: Float.NEGATIVE_INFINITY
        return frames.sortedByDescending { likeness(it) }.take(count).toSet()
    }

    private fun android.database.Cursor.getStringOrNull(i: Int): String? = if (isNull(i)) null else getString(i)
}
