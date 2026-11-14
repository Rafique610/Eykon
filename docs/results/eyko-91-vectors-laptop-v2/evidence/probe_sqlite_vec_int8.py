import sqlite3, sys, sqlite_vec, numpy as np, importlib.metadata as md
print("python", sys.version.split()[0], "| sqlite", sqlite3.sqlite_version, "| sqlite-vec", md.version("sqlite-vec"), "| numpy", np.__version__)
real = np.frombuffer(open("own_image_512.f32", "rb").read(), dtype="<f4").reshape(-1, 512)
print("own real vectors:", real.shape, "norms", np.round(np.linalg.norm(real, axis=1)[:3], 4))
rng = np.random.default_rng(31); rnd = rng.standard_normal((90, 512)).astype(np.float32); rnd /= np.linalg.norm(rnd, axis=1, keepdims=True)
con = sqlite3.connect(":memory:"); con.enable_load_extension(True); sqlite_vec.load(con)
def q8(v): return np.frombuffer(con.execute("select vec_quantize_int8(?, 'unit')", (v.tobytes(),)).fetchone()[0], dtype=np.int8)
for name, X in (("own real", real), ("random", rnd)):
    Q = np.stack([q8(x) for x in X]).astype(np.int32)
    levels = len(np.unique(Q)); mx = np.abs(X).max(axis=1)
    print(f"{name}: |component| max per vector median {np.median(mx):.3f}; int8 values used {Q.min()}..{Q.max()} ({levels} distinct of 256)")
    x = X[0]; print(f"  example: float {np.round(x[:5],4).tolist()} -> int8 {q8(x)[:5].tolist()}")
con.execute("create virtual table c using vec0(id integer primary key, e int8[512] distance_metric=cosine)")
con.executemany("insert into c(id, e) values (?, vec_quantize_int8(?, 'unit'))", [(i, real[i].tobytes()) for i in range(90)])
q = real[5] + 0.05 * rng.standard_normal(512).astype(np.float32); q /= np.linalg.norm(q)
got = [r[0] for r in con.execute("select id from c where e match vec_quantize_int8(?, 'unit') and k = 20", (q.astype(np.float32).tobytes(),))]
truth = list(np.argsort(-(real @ q))[:20])
print("int8 cosine knn works; recall@20 on 90 own vectors, 1 query:", len(set(got) & set(int(t) for t in truth)) / 20)
con.execute("create virtual table f using vec0(id integer primary key, e float[512] distance_metric=cosine)")
con.executemany("insert into f(id, e) values (?, ?)", [(i, real[i].tobytes()) for i in range(90)])
got = [r[0] for r in con.execute("select id from f where e match ? and k = 20", (q.astype(np.float32).tobytes(),))]
print("float32 cosine knn recall@20 (should be 1.0):", len(set(got) & set(int(t) for t in truth)) / 20)
