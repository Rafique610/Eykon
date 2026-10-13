package com.eykon.memory.video

import android.graphics.BitmapFactory
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import java.io.File

/**
 * Stage "filter" (card EYKO-5): drop useless frames with plain maths before any model runs.
 * Frames are taken in slots of a few seconds and at most the sharpest frame of each slot is kept.
 * A dropped frame keeps its row and its file, with kept = 0 and the reason.
 */
object VideoFilter {

    private const val TAG = "EykonVideo"

    fun run(db: SupportSQLiteDatabase, videoId: String) = run(db, videoId, FrameFilters.SLOT_FRAMES)

    /** [slotFrames] = 1 checks every frame on its own, as this stage did before slots. */
    fun run(db: SupportSQLiteDatabase, videoId: String, slotFrames: Int) {
        val videosDir = db.query("SELECT file_path FROM videos WHERE video_id = ?", arrayOf(videoId)).use { cursor ->
            if (!cursor.moveToFirst()) throw IllegalStateException("video $videoId is not in the database")
            File(cursor.getString(0)).parentFile?.parentFile ?: throw IllegalStateException("video file has no folder")
        }
        val frames = db.query("SELECT id, frame_no, path FROM frames WHERE video_id = ? ORDER BY frame_no", arrayOf(videoId)).use { cursor ->
            buildList { while (cursor.moveToNext()) add(Triple(cursor.getLong(0), cursor.getInt(1), cursor.getString(2))) }
        }

        val start = System.nanoTime()
        val thresholds = FrameFilters.Thresholds()
        val decisions = ArrayList<Pair<Long, String?>>(frames.size)
        var previousKept: Gray? = null
        for (slot in frames.chunked(slotFrames)) { // only one slot of pictures is in memory at a time
            val grays = slot.map { loadSmallGray(File(videosDir, it.third)) }
            val reasons = FrameFilters.pickSlot(previousKept, grays, thresholds)
            reasons.indexOf(null).takeIf { it >= 0 }?.let { previousKept = grays[it] }
            slot.forEachIndexed { i, (id, frameNo, _) ->
                decisions.add(id to reasons[i])
                if (Log.isLoggable(TAG, Log.DEBUG)) Log.d(TAG, "filter $videoId frame $frameNo: ${reasons[i] ?: "kept"}")
            }
        }
        val ms = (System.nanoTime() - start) / 1_000_000

        // Idempotent: every frame of the video gets its decision again, in one transaction.
        db.beginTransaction()
        try {
            db.execSQL("UPDATE frames SET kept = 1, drop_reason = NULL WHERE video_id = ?", arrayOf(videoId))
            for ((id, reason) in decisions) {
                if (reason != null) db.execSQL("UPDATE frames SET kept = 0, drop_reason = ? WHERE id = ?", arrayOf(reason, id))
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }

        val dropped = LinkedHashMap<String, Int>()
        decisions.mapNotNull { it.second }.forEach { dropped[it] = (dropped[it] ?: 0) + 1 }
        val detail = if (dropped.isEmpty()) "" else dropped.entries.joinToString(", ", " (", ")") { "${it.key} ${it.value}" }
        Log.i(TAG, "filter $videoId: kept ${frames.size - dropped.values.sum()} of ${frames.size}$detail in $ms ms")
    }

    fun loadSmallGray(file: File): Gray {
        val bitmap = BitmapFactory.decodeFile(file.absolutePath) ?: throw IllegalStateException("frame ${file.name} cannot be read")
        val pixels = IntArray(bitmap.width * bitmap.height)
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        return FrameFilters.smallGray(pixels, bitmap.width, bitmap.height).also { bitmap.recycle() }
    }
}
