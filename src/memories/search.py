import re
from pathlib import Path

import numpy as np

from src.config import Settings
from src.memories.database import get_connection
from src.memories.embedder import Embedder
from src.memories.models import MemoryRecord
from src.memories.repository import get_all_memories, get_memory_by_id

RRF_K = 60


def _dense_search(
    query: str,
    embedder: Embedder,
    all_memories: list[MemoryRecord],
) -> list[tuple[MemoryRecord, float]]:
    """Rank memories by cosine similarity using query embedding dot product."""
    if not all_memories:
        return []

    query_vector = np.array(embedder.embed(query), dtype=np.float32)
    mem_vectors = np.array([m.embedding for m in all_memories], dtype=np.float32)
    scores = np.dot(mem_vectors, query_vector)

    ranked = sorted(
        zip(all_memories, (float(s) for s in scores)),
        key=lambda x: x[1],
        reverse=True,
    )
    return ranked


def _sparse_search(
    query: str,
    db_path: Path | str | None = None,
) -> list[tuple[MemoryRecord, float]]:
    """Rank memories by SQLite FTS5 BM25 keyword matching."""
    words = re.findall(r"\w+", query)
    if not words:
        return []

    fts_query = " OR ".join(f'"{w}"' for w in words)
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT rowid, rank
            FROM memories_fts
            WHERE memories_fts MATCH ?
            ORDER BY rank ASC;
            """,
            (fts_query,),
        )
        rows = cursor.fetchall()
        results: list[tuple[MemoryRecord, float]] = []
        for row in rows:
            rec = get_memory_by_id(row["rowid"], db_path=db_path)
            if rec is not None:
                score = abs(float(row["rank"]))
                results.append((rec, score))
        return results
    except Exception:
        return []
    finally:
        conn.close()


def search_memories(
    query: str,
    embedder: Embedder | None = None,
    top_k: int | None = None,
    mode: str = "hybrid",
    db_path: Path | str | None = None,
) -> list[tuple[MemoryRecord, float]]:
    """Search stored memories using hybrid (dense + sparse RRF), semantic, or keyword retrieval."""
    settings = Settings()
    effective_top_k = top_k if top_k is not None else settings.TOP_K

    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    if mode == "keyword":
        sparse_hits = _sparse_search(cleaned_query, db_path=db_path)
        return sparse_hits[:effective_top_k]

    if embedder is None:
        embedder = Embedder()

    all_memories = get_all_memories(db_path=db_path)
    if not all_memories:
        return []

    dense_hits = _dense_search(cleaned_query, embedder, all_memories)

    if mode == "semantic":
        return dense_hits[:effective_top_k]

    # Hybrid Search: Combine dense + sparse via Reciprocal Rank Fusion (RRF)
    sparse_hits = _sparse_search(cleaned_query, db_path=db_path)

    rrf_scores: dict[int, float] = {}
    record_map: dict[int, MemoryRecord] = {m.id: m for m in all_memories if m.id is not None}

    for rank_idx, (record, _) in enumerate(dense_hits):
        if record.id is not None:
            rrf_scores[record.id] = rrf_scores.get(record.id, 0.0) + (1.0 / (RRF_K + rank_idx + 1))

    for rank_idx, (record, _) in enumerate(sparse_hits):
        if record.id is not None:
            rrf_scores[record.id] = rrf_scores.get(record.id, 0.0) + (1.0 / (RRF_K + rank_idx + 1))

    sorted_ids = sorted(rrf_scores.keys(), key=lambda mid: rrf_scores[mid], reverse=True)
    return [(record_map[mid], rrf_scores[mid]) for mid in sorted_ids[:effective_top_k]]
