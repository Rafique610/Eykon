import sqlite3

from src.video_memory import db

TABLES = (
    "videos", "frames", "audio_segments", "transcript_chunks", "scene_records",
    "video_texts", "video_texts_fts", "audio_windows", "image_vec", "text_vec", "audio_vec",
)

DDL = """
CREATE TABLE IF NOT EXISTS videos (
  video_id    TEXT PRIMARY KEY,            -- uuid4().hex
  file_path   TEXT NOT NULL,
  recorded_at TEXT NOT NULL,               -- ISO 8601, UTC
  duration_s  REAL NOT NULL DEFAULT 0,
  lat REAL, lon REAL,
  status      TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')),
  created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS frames (
  id          INTEGER PRIMARY KEY,
  video_id    TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  frame_no    INTEGER NOT NULL,
  t_s         REAL NOT NULL,               -- seconds from the start of the video
  path        TEXT NOT NULL,
  phash       TEXT,
  kept        INTEGER NOT NULL DEFAULT 1,
  drop_reason TEXT,                        -- dark | bright | blurry | still | duplicate of frame N
  UNIQUE (video_id, frame_no)
);
CREATE TABLE IF NOT EXISTS audio_segments (
  id INTEGER PRIMARY KEY,
  video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  start_s REAL NOT NULL, end_s REAL NOT NULL,
  is_speech INTEGER NOT NULL, loudness_db REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS transcript_chunks (
  id INTEGER PRIMARY KEY,
  video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  start_s REAL NOT NULL, end_s REAL NOT NULL,
  language TEXT, speaker TEXT, confidence REAL, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scene_records (
  frame_id INTEGER PRIMARY KEY REFERENCES frames(id) ON DELETE CASCADE,
  objects TEXT NOT NULL,                   -- JSON list of {"label", "conf"}
  action TEXT, place TEXT, people INTEGER NOT NULL DEFAULT 0,
  caption TEXT NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('A', 'B', 'C'))
);
CREATE TABLE IF NOT EXISTS video_texts (    -- captions and transcript chunks, for text vectors and BM25
  id INTEGER PRIMARY KEY,
  video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  source TEXT NOT NULL CHECK (source IN ('caption', 'transcript')),
  ref_id INTEGER NOT NULL,                 -- frames.id or transcript_chunks.id
  start_s REAL NOT NULL, end_s REAL NOT NULL,
  text TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS video_texts_fts USING fts5(text, content='video_texts', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS video_texts_ai AFTER INSERT ON video_texts BEGIN
  INSERT INTO video_texts_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS video_texts_ad AFTER DELETE ON video_texts BEGIN
  INSERT INTO video_texts_fts(video_texts_fts, rowid, text) VALUES('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS video_texts_au AFTER UPDATE ON video_texts BEGIN
  INSERT INTO video_texts_fts(video_texts_fts, rowid, text) VALUES('delete', old.id, old.text);
  INSERT INTO video_texts_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TABLE IF NOT EXISTS audio_windows (
  id INTEGER PRIMARY KEY,
  video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  start_s REAL NOT NULL, end_s REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS image_vec (frame_id  INTEGER PRIMARY KEY REFERENCES frames(id)        ON DELETE CASCADE, embedding BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS text_vec  (text_id   INTEGER PRIMARY KEY REFERENCES video_texts(id)   ON DELETE CASCADE, embedding BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS audio_vec (window_id INTEGER PRIMARY KEY REFERENCES audio_windows(id) ON DELETE CASCADE, embedding BLOB NOT NULL);
"""


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Idempotently create the video memory tables. Opens the app database when no connection is given."""
    own = conn is None
    conn = conn or db.connect()
    try:
        conn.executescript(DDL)
    finally:
        if own:
            conn.close()


def delete_video(conn: sqlite3.Connection, video_id: str) -> None:
    """Delete one video; every row that belongs to it cascades, vector tables included."""
    with conn:
        conn.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))
    db.clear_cache()


if __name__ == "__main__":
    connection = db.connect()
    init_db(connection)
    for name in TABLES:
        print(f"{name:<18} {connection.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]} rows")
    connection.close()
