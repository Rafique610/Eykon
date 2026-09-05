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
    # Filter out single-character tokens (e.g. 's' from possessives) unless that's all there is
    words = [w for w in re.findall(r"\w+", query) if len(w) > 1]
    if not words:
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


class SearchResult:
    """A search result holding the MemoryRecord and its constituent scores."""

    def __init__(
        self,
        record: MemoryRecord,
        score: float,
        semantic_score: float | None = None,
        bm25_score: float | None = None,
        match_type: str = "hybrid",
    ):
        self.record = record
        self.score = score
        self.semantic_score = semantic_score
        self.bm25_score = bm25_score
        self.match_type = match_type  # "both", "semantic", "bm25"

    def __iter__(self):
        """Allow backwards-compatible 2-tuple unpacking: rec, score = hit."""
        return iter((self.record, self.score))

    def __getitem__(self, index):
        """Allow backwards-compatible tuple indexing: hit[0], hit[1]."""
        return (self.record, self.score)[index]

    def __len__(self):
        return 2

    def __repr__(self):
        return (
            f"SearchResult(id={self.record.id}, score={self.score:.4f}, "
            f"semantic={self.semantic_score}, bm25={self.bm25_score}, match='{self.match_type}')"
        )


def search_memories(
    query: str,
    embedder: Embedder | None = None,
    top_k: int | None = None,
    mode: str = "hybrid",
    db_path: Path | str | None = None,
) -> list[SearchResult]:
    """Search stored memories using hybrid (top 5 both + intersection first), semantic, or keyword retrieval."""
    settings = Settings()
    effective_top_k = top_k if top_k is not None else settings.TOP_K

    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    if mode == "keyword":
        sparse_hits = _sparse_search(cleaned_query, db_path=db_path)
        return [
            SearchResult(
                record=rec,
                score=score,
                semantic_score=None,
                bm25_score=score,
                match_type="bm25",
            )
            for rec, score in sparse_hits[:effective_top_k]
        ]

    if embedder is None:
        embedder = Embedder()

    all_memories = get_all_memories(db_path=db_path)
    if not all_memories:
        return []

    dense_hits = _dense_search(cleaned_query, embedder, all_memories)

    if mode == "semantic":
        return [
            SearchResult(
                record=rec,
                score=score,
                semantic_score=score,
                bm25_score=None,
                match_type="semantic",
            )
            for rec, score in dense_hits[:effective_top_k]
        ]

    # Hybrid Search: Top 5 from semantic + top 5 from BM25.
    # Prioritize memories common to both, then fill with individual highest-scoring candidates.
    sparse_hits = _sparse_search(cleaned_query, db_path=db_path)

    pool_size = effective_top_k
    dense_top = dense_hits[:pool_size]
    sparse_top = sparse_hits[:pool_size]

    dense_scores = {rec.id: score for rec, score in dense_hits if rec.id is not None}
    dense_ranks = {rec.id: rank for rank, (rec, _) in enumerate(dense_top) if rec.id is not None}

    sparse_scores = {rec.id: score for rec, score in sparse_hits if rec.id is not None}
    sparse_ranks = {rec.id: rank for rank, (rec, _) in enumerate(sparse_top) if rec.id is not None}

    record_map: dict[int, MemoryRecord] = {m.id: m for m in all_memories if m.id is not None}

    # 1. Pick memories that are common in both top-5 lists
    common_ids = [mid for mid in dense_ranks if mid in sparse_ranks]
    common_results: list[SearchResult] = []
    for mid in common_ids:
        combined_score = (1.0 / (RRF_K + dense_ranks[mid] + 1)) + (1.0 / (RRF_K + sparse_ranks[mid] + 1))
        common_results.append(
            SearchResult(
                record=record_map[mid],
                score=combined_score,
                semantic_score=dense_scores.get(mid),
                bm25_score=sparse_scores.get(mid),
                match_type="both",
            )
        )
    common_results.sort(key=lambda x: x.score, reverse=True)

    # 2. If fewer than top_k, pick from individual lists
    individual_candidates: list[SearchResult] = []
    seen_ids = set(common_ids)

    for mid, rank in dense_ranks.items():
        if mid not in seen_ids:
            seen_ids.add(mid)
            score = 1.0 / (RRF_K + rank + 1)
            individual_candidates.append(
                SearchResult(
                    record=record_map[mid],
                    score=score,
                    semantic_score=dense_scores.get(mid),
                    bm25_score=sparse_scores.get(mid),
                    match_type="semantic",
                )
            )

    for mid, rank in sparse_ranks.items():
        if mid not in seen_ids:
            seen_ids.add(mid)
            score = 1.0 / (RRF_K + rank + 1)
            individual_candidates.append(
                SearchResult(
                    record=record_map[mid],
                    score=score,
                    semantic_score=dense_scores.get(mid),
                    bm25_score=sparse_scores.get(mid),
                    match_type="bm25",
                )
            )

    individual_candidates.sort(key=lambda x: x.score, reverse=True)

    final_results = common_results + individual_candidates
    return final_results[:effective_top_k]
