import sqlite3, sqlite_vec, numpy as np
real = np.frombuffer(open("own_image_512.f32", "rb").read(), dtype="<f4").reshape(-1, 512)
rng = np.random.default_rng(31)
con = sqlite3.connect(":memory:"); con.enable_load_extension(True); sqlite_vec.load(con)
con.execute("create virtual table f using vec0(id integer primary key, e float[512] distance_metric=cosine)")
con.execute("create virtual table g using vec0(id integer primary key, e float[512])")
for t in "fg": con.executemany(f"insert into {t}(id, e) values (?, ?)", [(i, real[i].tobytes()) for i in range(90)])
worst = {"f": 1.0, "g": 1.0}; gaps = []
for trial in range(200):
    q = real[trial % 90] + 0.05 * rng.standard_normal(512); q = (q / np.linalg.norm(q)).astype(np.float32)
    s = real.astype(np.float64) @ q.astype(np.float64); order = np.argsort(-s); truth = set(order[:20].tolist())
    gaps.append(s[order[19]] - s[order[20]])
    for t in "fg":
        got = {r[0] for r in con.execute(f"select id from {t} where e match ? and k = 20", (q.tobytes(),))}
        rec = len(got & truth) / 20
        if rec < worst[t]: worst[t] = rec; print(f"table {t} trial {trial}: recall {rec}, score gap rank20-rank21 = {gaps[-1]:.2e}, missing {sorted(truth-got)} got-extra {sorted(got-truth)}")
print("worst recall: cosine table", worst["f"], "| L2 table", worst["g"], "| smallest rank-20/21 gap", f"{min(gaps):.2e}")
