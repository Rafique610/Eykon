package com.eykon.memory.video

import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import java.io.File

/**
 * One step of processing a video. It gets the database and the video id.
 * A stage must be idempotent: it first removes the rows it writes for that video,
 * then writes them again, so a retry or a resume never duplicates rows.
 */
typealias Stage = (SupportSQLiteDatabase, String) -> Unit

object VideoPipeline {
    /** The stages in flow order. Each later card adds its ("name", function) here. */
    val STAGES: List<Pair<String, Stage>> = listOf(
        "split" to VideoSplit::run,
        "filter" to VideoFilter::run,
        "dedup" to VideoDedup::run,
        "scene" to VideoScene::run,
        "small_objects" to VideoSmallObjects::run,
        "embed_images" to VideoEmbedImages::run,
        "embed_texts" to VideoEmbedTexts::run,
        "link" to VideoLink::run,
        "latest" to VideoLatest::run,
        "finish" to VideoFinish::run,
    )

    /**
     * Raised when a stage in the middle changes what it writes. Videos finished under an older
     * version run again from the stage after the one [REDO_AFTER] gives for each newer version,
     * the earliest one when several versions were skipped.
     */
    const val VERSION = 5
    val REDO_AFTER: Map<Int, String> = mapOf(
        2 to "dedup", // D-FINE in "scene" and the new "small_objects" (card EYKO-32)
        3 to "scene", // captions always name personal things ("small_objects" writes every caption again)
        4 to "scene", // YOLOE-11L on every kept frame replaces OWLv2 on MobileCLIP-picked frames
        5 to "dedup", // first-person action prompts with smoothing (EYKO-60); YOLOE only on flagged frames (EYKO-63)
    )

    /** The stage to redo after, for a phone whose videos were finished under [from]; null when nothing changed. */
    fun redoAfter(from: Int): String? =
        REDO_AFTER.filterKeys { it > from }.values.minByOrNull { name -> STAGES.indexOfFirst { it.first == name } }
}

/**
 * Stage "finish" (card EYKO-16): every stage before it worked, so the video may now be searched.
 * It also deletes the picture files of dropped frames (card EYKO-59): on Ego4D clips they were about
 * 90 % of the 8.8 MB a minute of frames. Their rows stay, with the time and the reason they were dropped.
 * Done last so a retry of a failed stage still finds every file; a redo from "split" decodes them again,
 * but a redo from "filter" or "dedup" would not find them, so REDO_AFTER must never name "split" or "filter".
 */
object VideoFinish {
    private const val TAG = "EykonVideo"

    fun run(db: SupportSQLiteDatabase, videoId: String) {
        db.execSQL("UPDATE videos SET status = 'ready' WHERE video_id = ?", arrayOf(videoId))
        val deleted = deleteDropped(db, videoId)
        Log.i(TAG, "finish $videoId: ready; $deleted dropped frame files deleted")
    }

    /** Deletes the files of this video's frames with kept = 0; returns how many were deleted. */
    fun deleteDropped(db: SupportSQLiteDatabase, videoId: String): Int {
        val videosDir = db.query("SELECT file_path FROM videos WHERE video_id = ?", arrayOf(videoId)).use { c ->
            if (!c.moveToFirst()) return 0
            File(c.getString(0)).parentFile?.parentFile ?: return 0
        }
        val paths = db.query("SELECT path FROM frames WHERE video_id = ? AND kept = 0", arrayOf(videoId)).use { c ->
            buildList { while (c.moveToNext()) add(c.getString(0)) }
        }
        return paths.count { File(videosDir, it).delete() }
    }
}
