"""EYKO-91: the 13 vector search methods of the laptop benchmark v2.

Each method gets the unit vectors once in build() and keeps its OWN copy (a file, a matrix, an
index), so the runner can drop the source vectors and measure only what the method holds.
search(query, k) returns row ids, best first. Rows are numbered 0..n-1 everywhere.
"""
import heapq
import os
import sqlite3
import time

import numpy as np

BLOCK = 16_384  # rows converted to float32 at a time by the float16 / int8 methods


def top_k(scores: np.ndarray, k: int) -> np.ndarray:
    top = np.argpartition(-scores, k - 1)[:k]
    return top[np.argsort(-scores[top])]


def blob_file(vecs: np.ndarray, path: str) -> sqlite3.Connection:
    """The app's layout: one float32 BLOB per row in a plain SQLite table."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE image_vec (frame_id INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
    conn.executemany("INSERT INTO image_vec VALUES (?, ?)", ((i, v.tobytes()) for i, v in enumerate(vecs)))
    conn.commit()
    return conn


class Method:
    name = ""
    exact = True  # exact methods must reach recall 1.0, or the run stops
    max_n = None  # larger sizes are skipped
    path = None  # file whose size goes into file_mb

    def build(self, vecs: np.ndarray, workdir: str) -> dict:
        raise NotImplementedError

    def search(self, query: np.ndarray, k: int):
        raise NotImplementedError

    def file_mb(self):
        return os.path.getsize(self.path) / 1e6 if self.path else None


class BlobDisk(Method):
    """Read every BLOB from SQLite on every query, then numpy dot + top k (v1 'cold', phone diskMax)."""
    name, max_n = "blob_disk_dot", 20_000

    def build(self, vecs, workdir):
        self.dim, self.path = vecs.shape[1], os.path.join(workdir, "blob.db")
        self.conn = blob_file(vecs, self.path)
        return {}

    def search(self, query, k):
        rows = self.conn.execute("SELECT embedding FROM image_vec ORDER BY frame_id").fetchall()
        m = np.frombuffer(b"".join(r[0] for r in rows), dtype=np.float32).reshape(-1, self.dim)
        return top_k(m @ query, k)


class NumpyMemory(Method):
    """float32 matrix in memory; m @ q with OpenBLAS (default threads, or 1 thread)."""

    def __init__(self, one_thread=False):
        self.name = "blob_memory_numpy_1t" if one_thread else "blob_memory_numpy"
        self.one_thread = one_thread

    def build(self, vecs, workdir):
        self.m = vecs.copy()
        if self.one_thread:
            from threadpoolctl import threadpool_limits
            self.limit = threadpool_limits(1)  # stays on for this process
        return {}

    def search(self, query, k):
        return top_k(self.m @ query, k)


class PyLoop(Method):
    """Plain Python lists and loops, no numpy: how much of the phone gap is the code (B5)."""
    name, max_n = "blob_memory_pyloop", 20_000

    def build(self, vecs, workdir):
        self.rows = vecs.tolist()
        return {}

    def search(self, query, k):
        q = query.tolist()
        scores = [sum(a * b for a, b in zip(v, q)) for v in self.rows]
        return heapq.nlargest(k, range(len(scores)), key=scores.__getitem__)


class Float16Memory(Method):
    """Matrix kept as float16 (half the memory); dot in float32, block by block (EYKO-109)."""
    name, exact = "blob_memory_f16", False

    def build(self, vecs, workdir):
        self.m = vecs.astype(np.float16)
        return {}

    def search(self, query, k):
        scores = np.concatenate([self.m[i:i + BLOCK].astype(np.float32) @ query for i in range(0, len(self.m), BLOCK)])
        return top_k(scores, k)


class Int8Memory(Method):
    """int8 with one scale per vector (a quarter of the memory). Each block is widened to float32
    and dotted with the float32 query, then scaled: the byte x float loop a phone would run."""
    name, exact = "blob_memory_i8", False

    def build(self, vecs, workdir):
        self.scale = (np.abs(vecs).max(axis=1) / 127).astype(np.float32)
        self.m = np.round(vecs / self.scale[:, None]).astype(np.int8)
        return {}

    def scores(self, query):
        return np.concatenate([self.m[i:i + BLOCK].astype(np.float32) @ query for i in range(0, len(self.m), BLOCK)]) * self.scale

    def search(self, query, k):
        return top_k(self.scores(query), k)


class Int8Rescore(Int8Memory):
    """int8 picks the best 100, then their float32 BLOBs are read from SQLite and re-scored."""
    name, candidates = "blob_memory_i8_rescore", 100

    def build(self, vecs, workdir):
        self.dim, self.path = vecs.shape[1], os.path.join(workdir, "blob.db")
        self.conn = blob_file(vecs, self.path)
        return super().build(vecs, workdir)

    def search(self, query, k):
        ids = top_k(self.scores(query), self.candidates).tolist()
        rows = self.conn.execute(f"SELECT frame_id, embedding FROM image_vec WHERE frame_id IN ({','.join('?' * len(ids))})", ids).fetchall()
        found = np.array([r[0] for r in rows])
        m = np.frombuffer(b"".join(r[1] for r in rows), dtype=np.float32).reshape(-1, self.dim)
        return found[top_k(m @ query, k)]


class SqliteVec(Method):
    """sqlite-vec vec0 table, brute force inside SQLite; float32 or int8 ('unit' quantizer)."""

    def __init__(self, int8=False):
        self.int8, self.exact = int8, not int8
        self.name = "sqlite_vec_int8" if int8 else "sqlite_vec_f32"
        self.value = "vec_quantize_int8(?, 'unit')" if int8 else "?"

    def build(self, vecs, workdir):
        import sqlite_vec

        self.path = os.path.join(workdir, "vec.db")
        self.conn = sqlite3.connect(self.path)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        kind = "int8" if self.int8 else "float"
        self.conn.execute(f"CREATE VIRTUAL TABLE image_vec USING vec0(frame_id INTEGER PRIMARY KEY, e {kind}[{vecs.shape[1]}] distance_metric=cosine)")
        self.conn.executemany(f"INSERT INTO image_vec VALUES (?, {self.value})", ((i, v.tobytes()) for i, v in enumerate(vecs)))
        self.conn.commit()
        return {"sqlite_vec": self.conn.execute("SELECT vec_version()").fetchone()[0]}

    def search(self, query, k):
        sql = f"SELECT frame_id FROM image_vec WHERE e MATCH {self.value} AND k = ? ORDER BY distance"
        return [r[0] for r in self.conn.execute(sql, (query.tobytes(), k))]


class UsearchHnsw(Method):
    """usearch HNSW graph (EYKO-89's pick). Built with all threads, searched with one."""
    exact = False

    def __init__(self, connectivity, ef):
        self.name, self.connectivity, self.ef = f"usearch_hnsw_c{connectivity}_ef{ef}", connectivity, ef

    def build(self, vecs, workdir):
        from usearch.index import Index

        self.index = Index(ndim=vecs.shape[1], metric="cos", dtype="f32", connectivity=self.connectivity,
                           expansion_add=max(128, self.ef // 2), expansion_search=self.ef)
        start = time.perf_counter()
        self.index.add(np.arange(len(vecs)), vecs, threads=0)
        build_s = time.perf_counter() - start
        self.path = os.path.join(workdir, "index.usearch")
        self.index.save(self.path)
        return {"index_build_s": f"{build_s:.1f}", "expansion_add": max(128, self.ef // 2)}

    def search(self, query, k):
        return self.index.search(query, k, threads=1).keys


class UsearchExact(Method):
    """usearch brute force (exact=True) over a float32 copy, one thread: fast native code (B5)."""
    name = "usearch_exact_f32"

    def build(self, vecs, workdir):
        from usearch.index import MetricKind, search

        self.m, self.run = vecs.copy(), search
        self.metric = MetricKind.Cos
        return {}

    def search(self, query, k):
        return self.run(self.m, query, k, self.metric, exact=True, threads=1).keys


METHODS = {m.name: m for m in (
    BlobDisk(), NumpyMemory(), NumpyMemory(one_thread=True), PyLoop(), Float16Memory(), Int8Memory(),
    Int8Rescore(), SqliteVec(), SqliteVec(int8=True), UsearchHnsw(16, 64), UsearchHnsw(16, 256),
    UsearchHnsw(32, 1024), UsearchExact(),
)}
