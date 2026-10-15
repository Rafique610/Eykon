package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase

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
    const val VERSION = 4
    val REDO_AFTER: Map<Int, String> = mapOf(
        2 to "dedup", // D-FINE in "scene" and the new "small_objects" (card EYKO-32)
        3 to "scene", // captions always name personal things ("small_objects" writes every caption again)
        4 to "scene", // YOLOE-11L on every kept frame replaces OWLv2 on MobileCLIP-picked frames
    )

    /** The stage to redo after, for a phone whose videos were finished under [from]; null when nothing changed. */
    fun redoAfter(from: Int): String? =
        REDO_AFTER.filterKeys { it > from }.values.minByOrNull { name -> STAGES.indexOfFirst { it.first == name } }
}

/** Stage "finish" (card EYKO-16): every stage before it worked, so the video may now be searched. */
object VideoFinish {
    fun run(db: SupportSQLiteDatabase, videoId: String) =
        db.execSQL("UPDATE videos SET status = 'ready' WHERE video_id = ?", arrayOf(videoId))
}
