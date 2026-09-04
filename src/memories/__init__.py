"""Memories feature module: models, storage, embedding, and retrieval."""

from src.memories.database import get_connection, get_db_path, init_db
from src.memories.embedder import Embedder
from src.memories.models import MemoryRecord
from src.memories.repository import (
    clear_all_memories,
    count_memories,
    delete_memory,
    get_all_memories,
    get_memory_by_id,
    save_memory,
)

__all__ = [
    "MemoryRecord",
    "Embedder",
    "init_db",
    "get_connection",
    "get_db_path",
    "save_memory",
    "get_all_memories",
    "get_memory_by_id",
    "delete_memory",
    "count_memories",
    "clear_all_memories",
]
