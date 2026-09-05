"""Retrieval metrics for RAG benchmarking.

All functions take:
    retrieved_ids: ordered list of chunk IDs returned by search (rank 1 first)
    gold_ids:      set of chunk IDs that are considered relevant
    k:             cutoff rank
"""
from __future__ import annotations
import math


def hit_at_k(retrieved_ids: list[int], gold_ids: set[int], k: int) -> float:
    """1.0 if any gold chunk appears in the top-k retrieved results."""
    return 1.0 if any(rid in gold_ids for rid in retrieved_ids[:k]) else 0.0


def reciprocal_rank(retrieved_ids: list[int], gold_ids: set[int]) -> float:
    """1 / rank of the first gold chunk. 0.0 if not found in list."""
    for rank, rid in enumerate(retrieved_ids, 1):
        if rid in gold_ids:
            return 1.0 / rank
    return 0.0


def precision_at_k(retrieved_ids: list[int], gold_ids: set[int], k: int) -> float:
    """Fraction of top-k retrieved that are gold chunks."""
    if k == 0:
        return 0.0
    hits = sum(1 for rid in retrieved_ids[:k] if rid in gold_ids)
    return hits / k


def ndcg_at_k(retrieved_ids: list[int], gold_ids: set[int], k: int) -> float:
    """Normalised Discounted Cumulative Gain at k.
    Binary relevance: 1 if chunk is gold, 0 otherwise.
    """
    dcg = sum(
        1.0 / math.log2(i + 2)           # rank is 1-indexed; log2(rank+1)
        for i, rid in enumerate(retrieved_ids[:k])
        if rid in gold_ids
    )
    ideal_hits = min(len(gold_ids), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def aggregate(per_query: list[dict]) -> dict:
    """Compute mean of all metrics across a list of per-query result dicts."""
    n = len(per_query)
    if n == 0:
        return {}
    keys = ["hit@1", "hit@3", "hit@5", "mrr", "p@5", "ndcg@5", "latency_ms"]
    return {k: round(sum(r.get(k, 0) for r in per_query) / n, 4) for k in keys} | {"n": n}
