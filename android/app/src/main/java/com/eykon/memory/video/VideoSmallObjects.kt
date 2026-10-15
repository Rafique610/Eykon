package com.eykon.memory.video

import android.graphics.BitmapFactory
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.vision.Detection
import com.eykon.memory.ml.vision.YoloeDetector
import java.io.File

/** Finds the user's own small things in one frame file. */
typealias FindOwn = (File) -> List<Detection>

/**
 * Stage "small_objects" (card EYKO-32): YOLOE-11L looks for the user's own small things ("keys",
 * "earbuds": what D-FINE never names) in every kept frame. What it finds joins the frame's scene record
 * with source "own" and the caption is written again. Measured on the Pixel with D-FINE in the scene
 * step: 55 of 87 own things against 37 without this stage, about 30 s more for a 75 s clip
 * (docs/results/2026-10-14-detectors-open-vocabulary.md, "YOLOE-11L on the Pixel"). It replaced
 * OWLv2 on a third of the frames picked by MobileCLIP: 50 of 87 at about 58 s more.
 */
object VideoSmallObjects {

    /** Sources this stage writes; "owl" is from the OWLv2 version, replaced the same way. */
    val SOURCES = setOf("own", "owl")
    private const val TAG = "EykonVideo"

    fun run(db: SupportSQLiteDatabase, videoId: String) {
        val context = MemoryApp.instance
        try {
            run(db, videoId) { file ->
                val picture = BitmapFactory.decodeFile(file.absolutePath) ?: throw IllegalStateException("picture ${file.name} cannot be read")
                try { YoloeDetector.detect(context, picture) } finally { picture.recycle() }
            }
        } finally {
            YoloeDetector.close()
        }
    }

    private class Kept(val id: Long, val path: String, val objects: String, val people: Int, val place: String?, val action: String?)

    /** [findOwn] is YOLOE; tests pass their own. */
    fun run(db: SupportSQLiteDatabase, videoId: String, findOwn: FindOwn) {
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

        val start = System.nanoTime()
        val found = kept.associate { it.id to findOwn(File(videosDir, it.path)) }
        val ms = (System.nanoTime() - start) / 1_000_000

        db.beginTransaction()
        try {
            for (frame in kept) {
                // Idempotent: this stage's finds from an earlier run go first, then this run's are added
                val objects = VideoScene.objectsFrom(frame.objects).filter { it.source !in SOURCES } + found[frame.id].orEmpty()
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
        Log.i(TAG, "small_objects $videoId: YOLOE on ${kept.size} frames, ${found.values.sumOf { it.size }} found, in $ms ms")
    }

    private fun android.database.Cursor.getStringOrNull(i: Int): String? = if (isNull(i)) null else getString(i)
}
