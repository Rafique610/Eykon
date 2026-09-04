import json
from pathlib import Path

from src.memories.database import get_connection
from src.memories.models import MemoryRecord


def save_memory(record: MemoryRecord, db_path: Path | str | None = None) -> int:
    """Save a MemoryRecord into SQLite database.
    
    Sets and returns the auto-generated record.id.
    """
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO memories (text, embedding, timestamp, source_type)
                VALUES (?, ?, ?, ?);
                """,
                (
                    record.text,
                    json.dumps(record.embedding),
                    record.timestamp.isoformat(),
                    record.source_type,
                ),
            )
            record.id = cursor.lastrowid
            return record.id
    finally:
        conn.close()


def get_all_memories(db_path: Path | str | None = None) -> list[MemoryRecord]:
    """Retrieve all stored memories ordered by id ascending."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT id, text, embedding, timestamp, source_type
            FROM memories
            ORDER BY id ASC;
            """
        )
        rows = cursor.fetchall()
        return [
            MemoryRecord.from_dict(
                {
                    "id": row["id"],
                    "text": row["text"],
                    "embedding": row["embedding"],
                    "timestamp": row["timestamp"],
                    "source_type": row["source_type"],
                }
            )
            for row in rows
        ]
    finally:
        conn.close()


def get_memory_by_id(memory_id: int, db_path: Path | str | None = None) -> MemoryRecord | None:
    """Retrieve a single memory by its ID, or None if not found."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT id, text, embedding, timestamp, source_type
            FROM memories
            WHERE id = ?;
            """,
            (memory_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return MemoryRecord.from_dict(
            {
                "id": row["id"],
                "text": row["text"],
                "embedding": row["embedding"],
                "timestamp": row["timestamp"],
                "source_type": row["source_type"],
            }
        )
    finally:
        conn.close()


def delete_memory(memory_id: int, db_path: Path | str | None = None) -> bool:
    """Delete a memory record by its ID. Returns True if a record was deleted."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                DELETE FROM memories
                WHERE id = ?;
                """,
                (memory_id,),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def count_memories(db_path: Path | str | None = None) -> int:
    """Return the total number of stored memories."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) AS count FROM memories;")
        row = cursor.fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()


def clear_all_memories(db_path: Path | str | None = None) -> int:
    """Delete all stored memories (useful for resets or tests). Returns count of deleted rows."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM memories;")
            return cursor.rowcount
    finally:
        conn.close()
