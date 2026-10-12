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
    )
}
