"""Cross-encoder re-ranker for second-stage relevance scoring."""
from __future__ import annotations

from sentence_transformers import CrossEncoder

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    """Lazy singleton — loads once, reuses across calls."""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(_MODEL_NAME)
    return _reranker


def rerank(query: str, texts: list[str]) -> list[float]:
    """Score each (query, text) pair. Returns list of relevance scores."""
    if not texts:
        return []
    model = get_reranker()
    pairs = [(query, t) for t in texts]
    scores = model.predict(pairs)
    
    # If there's only one pair, predict returns a scalar float. We need a list.
    if isinstance(scores, float):
        return [scores]
    return scores.tolist()
