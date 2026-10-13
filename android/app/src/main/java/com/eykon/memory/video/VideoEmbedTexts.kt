package com.eykon.memory.video

import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.embedder.BgeEmbedder

/**
 * Stage "embed_texts" (card EYKO-12): every caption, and every transcript chunk once speech is
 * built, becomes a row in video_texts. That makes it searchable two ways: by keyword (the
 * triggers keep the video_texts_fts index in step) and by meaning (a bge-small vector in
 * text_vec). A video with no transcript chunks is normal.
 */
object VideoEmbedTexts {

    private const val TAG = "EykonVideo"

    private class Text(val source: String, val refId: Long, val startS: Double, val endS: Double, val text: String)

    fun run(db: SupportSQLiteDatabase, videoId: String) =
        run(db, videoId) { text -> BgeEmbedder.embed(MemoryApp.instance, text) }

    /** [embed] turns a text into a vector of length 1; tests pass their own. */
    fun run(db: SupportSQLiteDatabase, videoId: String, embed: (String) -> FloatArray) {
        val texts = db.query(
            "SELECT 'caption', f.id, f.t_s, f.t_s, s.caption, f.t_s AS at FROM scene_records s JOIN frames f ON f.id = s.frame_id WHERE f.video_id = ? " +
                "UNION ALL SELECT 'transcript', id, start_s, end_s, text, start_s FROM transcript_chunks WHERE video_id = ? ORDER BY at",
            arrayOf(videoId, videoId),
        ).use { c ->
            buildList { while (c.moveToNext()) add(Text(c.getString(0), c.getLong(1), c.getDouble(2), c.getDouble(3), c.getString(4))) }
        }
        val start = System.nanoTime()
        val vectors = texts.map { embed(it.text) }

        db.beginTransaction()
        try {
            // Idempotent: this video's vectors and texts from an earlier run go first (the triggers clean the keyword index).
            db.execSQL("DELETE FROM text_vec WHERE text_id IN (SELECT id FROM video_texts WHERE video_id = ?)", arrayOf(videoId))
            db.execSQL("DELETE FROM video_texts WHERE video_id = ?", arrayOf(videoId))
            db.compileStatement("INSERT INTO video_texts (video_id, source, ref_id, start_s, end_s, text) VALUES (?, ?, ?, ?, ?, ?)").use { insert ->
                texts.forEachIndexed { i, text ->
                    insert.bindString(1, videoId)
                    insert.bindString(2, text.source)
                    insert.bindLong(3, text.refId)
                    insert.bindDouble(4, text.startS)
                    insert.bindDouble(5, text.endS)
                    insert.bindString(6, text.text)
                    VideoVectors.put(db, "text_vec", insert.executeInsert(), vectors[i])
                }
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        VideoVectors.clearCache("text_vec")
        val ms = (System.nanoTime() - start) / 1_000_000
        Log.i(TAG, "embed_texts $videoId: ${texts.size} texts (${texts.count { it.source == "caption" }} captions, ${texts.count { it.source == "transcript" }} transcript chunks) in $ms ms")
    }
}
