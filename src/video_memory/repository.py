import sqlite3
from dataclasses import asdict

from src.video_memory.models import Video


def insert_video(conn: sqlite3.Connection, video: Video) -> None:
    """Insert one videos row. The caller commits."""
    conn.execute(
        "INSERT INTO videos (video_id, file_path, recorded_at, created_at, duration_s, lat, lon, status) "
        "VALUES (:video_id, :file_path, :recorded_at, :created_at, :duration_s, :lat, :lon, :status)",
        asdict(video),
    )


def get_video(conn: sqlite3.Connection, video_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
