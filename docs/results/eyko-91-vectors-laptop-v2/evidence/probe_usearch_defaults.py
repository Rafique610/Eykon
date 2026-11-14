import time, importlib.metadata as md, numpy as np
from usearch.index import Index
print("usearch", md.version("usearch"))
rng = np.random.default_rng(0); n, d = 20000, 512
X = rng.standard_normal((n, d)).astype(np.float32); X /= np.linalg.norm(X, axis=1, keepdims=True)
Q = rng.standard_normal((20, d)).astype(np.float32); Q /= np.linalg.norm(Q, axis=1, keepdims=True)
truth = np.argsort(-(Q @ X.T), axis=1)[:, :20]
for dtype in ("f32", "f16", "i8"):
    idx = Index(ndim=d, metric="cos", dtype=dtype)
    t = time.perf_counter(); idx.add(np.arange(n), X); build = time.perf_counter() - t
    for exact in (False, True):
        t = time.perf_counter(); m = idx.search(Q, 20, exact=exact); ms = (time.perf_counter() - t) * 1000 / len(Q)
        rec = np.mean([len(set(m.keys[i]) & set(truth[i])) / 20 for i in range(len(Q))])
        print(f"{dtype} exact={exact}: build {build:.1f}s, {ms:.2f} ms/query, recall@20 {rec:.3f}, idx bytes {idx.memory_usage if hasattr(idx,'memory_usage') else 'n/a'}")
print("Index params:", {k: getattr(idx, k) for k in ("connectivity", "expansion_add", "expansion_search") if hasattr(idx, k)})
try:
    import hnswlib; print("hnswlib", md.version("hnswlib"))
except Exception as e: print("hnswlib not importable:", e)
