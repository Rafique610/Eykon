package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase

/**
 * Video memory tables. Same table and column names as the laptop's
 * src/video_memory/schema.py, which is the shared design for both sides.
 * One difference: the phone's SQLite has no FTS5, so the keyword index is fts4.
 */
object VideoSchema {

    val TABLES = listOf(
        "videos", "frames", "audio_segments", "transcript_chunks", "scene_records",
        "video_texts", "video_texts_fts", "audio_windows", "image_vec", "text_vec", "audio_vec",
    )

    private val STATEMENTS = listOf(
        """
        CREATE TABLE IF NOT EXISTS videos (
          video_id    TEXT PRIMARY KEY,
          file_path   TEXT NOT NULL,
          recorded_at TEXT NOT NULL,
          duration_s  REAL NOT NULL DEFAULT 0,
          lat REAL, lon REAL,
          status      TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')),
          created_at  TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS frames (
          id          INTEGER PRIMARY KEY,
          video_id    TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
          frame_no    INTEGER NOT NULL,
          t_s         REAL NOT NULL,
          path        TEXT NOT NULL,
          phash       TEXT,
          kept        INTEGER NOT NULL DEFAULT 1,
          drop_reason TEXT,
          UNIQUE (video_id, frame_no)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audio_segments (
          id INTEGER PRIMARY KEY,
          video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
          start_s REAL NOT NULL, end_s REAL NOT NULL,
          is_speech INTEGER NOT NULL, loudness_db REAL NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS transcript_chunks (
          id INTEGER PRIMARY KEY,
          video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
          start_s REAL NOT NULL, end_s REAL NOT NULL,
          language TEXT, speaker TEXT, confidence REAL, text TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS scene_records (
          frame_id INTEGER PRIMARY KEY REFERENCES frames(id) ON DELETE CASCADE,
          objects TEXT NOT NULL,
          action TEXT, place TEXT, people INTEGER NOT NULL DEFAULT 0,
          caption TEXT NOT NULL,
          source TEXT NOT NULL CHECK (source IN ('A', 'B', 'C'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS video_texts (
          id INTEGER PRIMARY KEY,
          video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
          source TEXT NOT NULL CHECK (source IN ('caption', 'transcript')),
          ref_id INTEGER NOT NULL,
          start_s REAL NOT NULL, end_s REAL NOT NULL,
          text TEXT NOT NULL
        )
        """,
        "CREATE VIRTUAL TABLE IF NOT EXISTS video_texts_fts USING fts4(text, content=`video_texts`)",
        // fts4 sync triggers. The ('delete', ...) insert used with FTS5 is not valid in fts4:
        // rows are removed with a plain DELETE before the content row changes.
        """
        CREATE TRIGGER IF NOT EXISTS video_texts_fts_ai AFTER INSERT ON video_texts BEGIN
          INSERT INTO video_texts_fts(docid, text) VALUES (new.id, new.text);
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS video_texts_fts_bd BEFORE DELETE ON video_texts BEGIN
          DELETE FROM video_texts_fts WHERE docid = old.id;
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS video_texts_fts_bu BEFORE UPDATE ON video_texts BEGIN
          DELETE FROM video_texts_fts WHERE docid = old.id;
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS video_texts_fts_au AFTER UPDATE ON video_texts BEGIN
          INSERT INTO video_texts_fts(docid, text) VALUES (new.id, new.text);
        END
        """,
        """
        CREATE TABLE IF NOT EXISTS audio_windows (
          id INTEGER PRIMARY KEY,
          video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
          start_s REAL NOT NULL, end_s REAL NOT NULL
        )
        """,
        "CREATE TABLE IF NOT EXISTS image_vec (frame_id INTEGER PRIMARY KEY REFERENCES frames(id) ON DELETE CASCADE, embedding BLOB NOT NULL)",
        "CREATE TABLE IF NOT EXISTS text_vec (text_id INTEGER PRIMARY KEY REFERENCES video_texts(id) ON DELETE CASCADE, embedding BLOB NOT NULL)",
        "CREATE TABLE IF NOT EXISTS audio_vec (window_id INTEGER PRIMARY KEY REFERENCES audio_windows(id) ON DELETE CASCADE, embedding BLOB NOT NULL)",
    )

    /** Idempotent: safe to run on every open. */
    fun create(db: SupportSQLiteDatabase) {
        STATEMENTS.forEach { db.execSQL(it.trimIndent()) }
    }
}
