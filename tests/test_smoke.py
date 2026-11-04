import sqlite3

from src.config import Settings
from src.memories.database import init_db


def test_settings_point_at_the_memories_database():
    assert Settings().DB_PATH.endswith("memories.db")


def test_init_db_is_idempotent(tmp_path):
    db = tmp_path / "memories.db"
    init_db(db)
    init_db(db)
    conn = sqlite3.connect(db)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    finally:
        conn.close()
    assert {"memories", "memories_fts"} <= tables
