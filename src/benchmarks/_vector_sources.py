"""EYKO-91: the test vectors and queries for the laptop vector benchmark v2, and recall@k with ties.

S1 "random": Gaussian unit vectors, seed 31; queries seed 90 (as EYKO-90 and v1).
S2 "real": the phones' own-clip vectors (90 per table), then noisy copies (0.01 per number);
queries are own frames with noise 0.05, seed 90. Same recipe as BenchKit.kt TestVectors, drawn
with numpy, so it matches the phones in kind but not bit for bit.
"""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "android/app/src/androidTest/assets/vectors"
LABELS = {"random": "random_unit_seed31", "real": "real_own_clips_90+noise"}
TIE_TOLERANCE = 1e-6


def unit(v: np.ndarray) -> np.ndarray:
    """Scale each row to length 1, in place."""
    v /= np.linalg.norm(v, axis=-1, keepdims=True)
    return v


def own_vectors(dim: int = 512) -> np.ndarray:
    """The committed own-clip vectors (float32, little endian), one row per frame or caption."""
    name = "own_image_512.f32" if dim == 512 else "own_text_384.f32"
    return np.fromfile(ASSETS / name, dtype="<f4").reshape(-1, dim)


def vectors(source: str, n: int, dim: int = 512) -> np.ndarray:
    """n unit vectors. A smaller n is always the first rows of a larger one (sizes nest)."""
    rng = np.random.default_rng(31)
    if source == "random":
        return unit(rng.standard_normal((n, dim), dtype=np.float32))
    if source != "real":
        raise ValueError(f"unknown source {source!r}")
    base = own_vectors(dim)
    out = base[np.arange(n) % len(base)]  # fancy indexing copies
    noisy = out[len(base):]
    noisy += 0.01 * rng.standard_normal(noisy.shape, dtype=np.float32)
    unit(noisy)
    return out


def queries(source: str, count: int, dim: int = 512) -> np.ndarray:
    """count unit query vectors, the same for every method and size."""
    rng = np.random.default_rng(90)
    if source == "random":
        return unit(rng.standard_normal((count, dim), dtype=np.float32))
    base = own_vectors(dim)
    picked = base[(np.arange(count) * 7) % len(base)]
    return unit(picked + 0.05 * rng.standard_normal(picked.shape, dtype=np.float32))


def label(source: str) -> str:
    return LABELS[source]


def exact_top(vecs: np.ndarray, query: np.ndarray, k: int) -> np.ndarray:
    """Row ids of the k best dot products, best first (the float32 reference)."""
    scores = vecs @ query
    top = np.argpartition(-scores, k - 1)[:k]
    return top[np.argsort(-scores[top])]


def recall_at_k(vecs: np.ndarray, query: np.ndarray, returned, k: int = 20) -> float:
    """Share of the k results that are truly among the best k, counting ties.

    A returned row is a hit when its exact score is at least the exact k-th best score minus
    TIE_TOLERANCE, so returning either copy of two identical vectors counts. Repeated ids,
    negative ids (usearch's "no result") and anything past the first k count once or not at all.
    """
    return recall_from_scores(vecs @ query, returned, k)


def recall_from_scores(scores: np.ndarray, returned, k: int = 20) -> float:
    """recall_at_k from the exact scores of every row for one query (saved before the run)."""
    kth = np.partition(scores, len(scores) - k)[len(scores) - k]
    ids = {int(i) for i in list(returned)[:k] if 0 <= int(i) < len(scores)}
    return sum(scores[i] >= kth - TIE_TOLERANCE for i in ids) / k


def mean_recall(vecs: np.ndarray, qs: np.ndarray, results, k: int = 20) -> float:
    """recall_at_k averaged over queries; results[i] are the ids returned for qs[i]."""
    return float(np.mean([recall_at_k(vecs, q, r, k) for q, r in zip(qs, results)]))
