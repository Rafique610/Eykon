import time, importlib.metadata as md, numpy as np
from usearch.index import Index
rng = np.random.default_rng(0); n, d = 20000, 512
X = rng.standard_normal((n, d)).astype(np.float32); X /= np.linalg.norm(X, axis=1, keepdims=True)
Q = rng.standard_normal((20, d)).astype(np.float32); Q /= np.linalg.norm(Q, axis=1, keepdims=True)
S = Q @ X.T; truth = np.argsort(-S, axis=1)[:, :20]
print(f"random 20k: true top-20 cosine median {np.median(np.sort(S,axis=1)[:,-20:]):.3f}, mean of all {S.mean():.3f}, std {S.std():.3f}")
for conn, ef in ((16, 64), (16, 256), (16, 1024), (32, 1024), (32, 4096)):
    idx = Index(ndim=d, metric="cos", dtype="f32", connectivity=conn, expansion_add=max(128, ef // 2), expansion_search=ef)
    t = time.perf_counter(); idx.add(np.arange(n), X, threads=0); b = time.perf_counter() - t
    t = time.perf_counter(); m = idx.search(Q, 20, threads=1); ms = (time.perf_counter() - t) * 1000 / len(Q)
    rec = np.mean([len(set(m.keys[i]) & set(truth[i])) / 20 for i in range(len(Q))])
    print(f"f32 connectivity {conn:>2} expansion_search {ef:>4}: build {b:5.1f}s, {ms:6.2f} ms/query (1 thread), recall@20 {rec:.3f}")
t = time.perf_counter(); [np.argpartition(-(X @ q), 20)[:20] for q in Q]; print(f"numpy exact (default threads) {(time.perf_counter()-t)*1000/len(Q):.2f} ms/query")
