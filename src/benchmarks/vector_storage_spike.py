"""EYKO-31 spike, laptop half: sqlite-vec KNN vs float32 BLOB + brute-force cosine. Run: task spike-laptop-vectors"""
import os
import sqlite3
import statistics
import sys
import tempfile
import time

import numpy as np
import psutil

DIM, QUERIES, K = 512, 20, 20
rng = np.random.default_rng(31)


def unit(n):
    v = rng.standard_normal((n, DIM)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def timed(fn, queries):
    out = []
    for q in queries:
        t = time.perf_counter()
        fn(q)
        out.append((time.perf_counter() - t) * 1000)
    return statistics.median(out), max(out)


def blob_run(path, vecs, queries):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE image_vec (frame_id INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
    conn.executemany("INSERT INTO image_vec VALUES (?, ?)", ((i, v.tobytes()) for i, v in enumerate(vecs)))
    conn.commit()

    def cold(q):  # read every row from SQLite, then dot product
        rows = conn.execute("SELECT frame_id, embedding FROM image_vec").fetchall()
        m = np.frombuffer(b"".join(r[1] for r in rows), dtype=np.float32).reshape(-1, DIM)
        return np.argsort(m @ q)[-K:]

    rows = conn.execute("SELECT frame_id, embedding FROM image_vec").fetchall()
    m = np.frombuffer(b"".join(r[1] for r in rows), dtype=np.float32).reshape(-1, DIM)

    def warm(q):  # matrix already in memory
        return np.argsort(m @ q)[-K:]

    res = timed(cold, queries), timed(warm, queries)
    conn.close()
    return res


def vec_run(path, vecs, queries):
    import sqlite_vec

    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.execute(f"CREATE VIRTUAL TABLE image_vec USING vec0(frame_id INTEGER PRIMARY KEY, embedding float[{DIM}])")
    conn.executemany("INSERT INTO image_vec VALUES (?, ?)", ((i, v.tobytes()) for i, v in enumerate(vecs)))
    conn.commit()
    version = conn.execute("select vec_version()").fetchone()[0]

    def knn(q):
        return conn.execute(
            "SELECT frame_id, distance FROM image_vec WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (q.tobytes(), K),
        ).fetchall()

    res = timed(knn, queries)
    conn.close()
    return version, res


tmp = tempfile.mkdtemp(prefix="eyko31_")
proc = psutil.Process()
print(f"python {sys.version.split()[0]}  sqlite {sqlite3.sqlite_version}  numpy {np.__version__}  cpu threads {os.cpu_count()}")
for n in (5_000, 20_000):
    vecs, queries = unit(n), unit(QUERIES)
    for name in ("blob", "vec"):
        p = os.path.join(tmp, f"{name}_{n}.db")
        if os.path.exists(p):
            os.remove(p)
    (cold_med, cold_max), (warm_med, warm_max) = blob_run(os.path.join(tmp, f"blob_{n}.db"), vecs, queries)
    version, (v_med, v_max) = vec_run(os.path.join(tmp, f"vec_{n}.db"), vecs, queries)
    # same top-1 from both methods?
    print(f"n={n:>6}  BLOB read+dot: median {cold_med:7.2f} ms  worst {cold_max:7.2f} ms")
    print(f"n={n:>6}  BLOB in-memory dot: median {warm_med:7.2f} ms  worst {warm_max:7.2f} ms")
    print(f"n={n:>6}  sqlite-vec {version}: median {v_med:7.2f} ms  worst {v_max:7.2f} ms")
    print(f"          file sizes: blob {os.path.getsize(os.path.join(tmp, f'blob_{n}.db'))/1e6:.1f} MB, vec {os.path.getsize(os.path.join(tmp, f'vec_{n}.db'))/1e6:.1f} MB")
print(f"peak RSS {proc.memory_info().peak_wset/1e6:.0f} MB" if hasattr(proc.memory_info(), "peak_wset") else f"RSS {proc.memory_info().rss/1e6:.0f} MB")
