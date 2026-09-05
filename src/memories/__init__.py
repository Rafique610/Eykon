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
    save_memories,
    save_memory,
)
from src.memories.search import SearchResult, search_memories
from src.memories.service import (
    chunk_text_by_tokens,
    create_memories_from_text,
    create_memory_from_text,
)

__all__ = [
    "MemoryRecord",
    "SearchResult",
    "Embedder",
    "create_memory_from_text",
    "create_memories_from_text",
    "chunk_text_by_tokens",
    "search_memories",
    "init_db",
    "get_connection",
    "get_db_path",
    "save_memory",
    "save_memories",
    "get_all_memories",
    "get_memory_by_id",
    "delete_memory",
    "count_memories",
    "clear_all_memories",
]


