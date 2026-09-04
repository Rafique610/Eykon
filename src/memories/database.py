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
                    source_type TEXT NOT NULL DEFAULT 'text'
                );
                """
            )
    finally:
        conn.close()
