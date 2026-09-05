import sqlite3
from pathlib import Path

from src.config import Settings


def get_db_path() -> Path:
    """Return the resolved Path to the SQLite database file, ensuring parent dirs exist."""
    settings = Settings()
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return an open SQLite connection configured with sqlite3.Row factory."""
    target_path = Path(db_path) if db_path else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    """Idempotently initialize the SQLite database and create memories table if missing."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'text',
                    metadata TEXT NOT NULL DEFAULT '{}'
                );
                """
            )
            # Idempotent migration: ensure metadata column exists if table was created earlier
            cursor = conn.execute("PRAGMA table_info(memories);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "metadata" not in columns:
                conn.execute("ALTER TABLE memories ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}';")

            # Create FTS5 virtual table for keyword search
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    text,
                    content='memories',
                    content_rowid='id'
                );
                """
            )

            # Keep FTS5 table in sync with memories table via SQLite triggers
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
                END;
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, text) VALUES('delete', old.id, old.text);
                END;
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, text) VALUES('delete', old.id, old.text);
                    INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
                END;
                """
            )
            # Ensure any pre-existing records are indexed into FTS5
            conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild');")
    finally:
        conn.close()

