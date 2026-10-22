import sqlite3
from pathlib import Path

import numpy as np

from src.config import Settings
from src.memories.database import get_connection

# table -> (id column, Settings field holding its dimension). Fixed names, never user input.
VEC_TABLES = {
    "image_vec": ("frame_id", "video_image_dim"),
    "text_vec": ("text_id", "video_text_dim"),
    "audio_vec": ("window_id", "video_audio_dim"),
}
_CACHE: dict = {}


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """A connection to the app database with foreign keys on."""
    conn = get_connection(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def put_vector(conn: sqlite3.Connection, table: str, row_id: int, vec: np.ndarray) -> None:
    """Store one L2-normalised vector as float32 bytes. The caller commits."""
    id_col, dim_field = VEC_TABLES[table]
    dim = getattr(Settings(), dim_field)
    if vec.shape != (dim,):
        raise ValueError(f"{table} expects {dim} numbers, got {vec.shape}")
    conn.execute(
        f"INSERT OR REPLACE INTO {table} ({id_col}, embedding) VALUES (?, ?)",
        (row_id, vec.astype(np.float32).tobytes()),
    )
    clear_cache(table)


def clear_cache(table: str | None = None) -> None:
    if table is None:
        _CACHE.clear()
    else:
        _CACHE.pop(table, None)


def knn(conn: sqlite3.Connection, table: str, query: np.ndarray, k: int) -> list[tuple[int, float]]:
    """Top-k (id, cosine) for a normalised query. The table is read into memory once, not per query."""
    id_col, _ = VEC_TABLES[table]
    stamp = tuple(conn.execute(f"SELECT COUNT(*), MAX({id_col}) FROM {table}").fetchone())
    if table not in _CACHE or _CACHE[table][0] != stamp:  # another process added or removed rows
        rows = conn.execute(f"SELECT {id_col}, embedding FROM {table} ORDER BY {id_col}").fetchall()
        ids = np.array([r[0] for r in rows], dtype=np.int64)
        matrix = np.frombuffer(b"".join(r[1] for r in rows), dtype=np.float32).reshape(len(rows), -1) if rows else None
        _CACHE[table] = (stamp, ids, matrix)
    _, ids, matrix = _CACHE[table]
    if matrix is None:
        return []
    scores = matrix @ query.astype(np.float32)
    top = np.argsort(scores)[::-1][:k]
    return [(int(ids[i]), float(scores[i])) for i in top]
