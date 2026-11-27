"""Hypotheses 2 + 3 (decision re-check, 26 Nov): can search read an int8 copy of the vectors and still return EXACTLY the app's
windows? Laptop. Run: task int8-windows

The app (VideoSearch.frames) scores every kept frame against the phrase (float32, MAPPED_NATIVE), then walks the frames best
first: a frame inside a window already taken in its video is skipped, otherwise it seeds a window that grows over neighbours
scoring >= 0.85 x the seed (gap <= 10 s); it stops at 20 windows. ADR 0001 rules out top-k indexes because "the app needs
every frame's score". Tested here:

  exact   the app's rule on exact float32 scores of every frame (the reference);
  int8    one int8 pass over every frame (one scale per vector, the phrase quantised too), then float32 scores only for
          (a) the best M frames of the int8 pass and (b) the neighbours a window looks at; windows are grown on those
          exact scores. A per-row error bound certifies the result: no frame left out of (a) can beat the weakest seed
          used. If the bound cannot certify it, M doubles; past the whole table it is the exact search.

Data: 100,000 COCO photo vectors (EYKO-113, MobileCLIP-S2, data/eyko91_coco) cut into "videos" of 100 frames, 1/3 s apart,
in id order, plus our own 90 clip frames (android/app/src/androidTest/assets/vectors) as one real video; queries: 21 COCO
captions + 21 EPIC narrations (data/eyko91_*/queries_512.f32) + 10 own phrases. COCO photos in a "video" are unrelated, so
windows are short; the 90 own frames are real neighbours. Identity is the question, not window quality.
Writes docs/results/int8-windows/int8-windows.json.
"""

import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/results/int8-windows"
GROW, GAP_S, HALF_S, K = np.float32(0.85), 10.0, 1.5, 20
PHRASES = ["keys", "earbuds", "a laptop", "a cup", "a chair", "a phone", "a book", "a person", "a table", "a bag"]


def load():
    coco = np.fromfile(ROOT / "data/eyko91_coco/images_512.f32", dtype=np.float32).reshape(-1, 512)
    own = np.fromfile(ROOT / "android/app/src/androidTest/assets/vectors/own_image_512.f32", dtype=np.float32).reshape(-1, 512)
    vecs = np.vstack([own, coco])
    vid = np.concatenate([np.zeros(len(own), np.int64), 1 + np.arange(len(coco)) // 100])
    t = np.concatenate([np.arange(len(own)) / 3.0, (np.arange(len(coco)) % 100) / 3.0])
    qs = [np.fromfile(ROOT / f"data/{d}/queries_512.f32", dtype=np.float32).reshape(-1, 512) for d in ("eyko91_coco", "eyko91_epic")]
    try:  # own phrases through the app's text encoder, if the model is here
        import onnxruntime as ort
        import open_clip
        tok = open_clip.get_tokenizer("MobileCLIP-S2")
        sess = ort.InferenceSession(str(ROOT / "models/mobileclip_s2_text.onnx"), providers=["CPUExecutionProvider"])
        p = np.vstack([sess.run(None, {"tokens": tok([x]).numpy().astype(np.int64)})[0][0] for x in PHRASES]).astype(np.float32)
        qs.append(p / np.linalg.norm(p, axis=1, keepdims=True))
    except Exception as e:  # noqa: BLE001
        print("own phrases skipped:", e)
    return vecs, vid, t, np.vstack(qs)


def runs(vid):
    """Start and end row of each video (rows are already in video, time order, as the app's query sorts them)."""
    edges = np.flatnonzero(np.diff(vid)) + 1
    starts = np.concatenate([[0], edges])
    return starts, np.concatenate([edges, [len(vid)]])


def walk(order, score_of, vid, t, starts, ends, run_of):
    """The app's loop. order: rows best first; score_of(row) gives the exact float32 score (computed on demand)."""
    taken, hits, used = {}, [], []
    for row in order:
        v = run_of[row]
        if any(a <= t[row] <= b for a, b in taken.get(v, [])):
            continue
        s = score_of(row)
        floor = GROW * s
        lo = hi = row
        while lo > starts[v] and score_of(lo - 1) >= floor and t[lo] - t[lo - 1] <= GAP_S:
            lo -= 1
        while hi < ends[v] - 1 and score_of(hi + 1) >= floor and t[hi + 1] - t[hi] <= GAP_S:
            hi += 1
        w = (max(0.0, t[lo] - HALF_S), t[hi] + HALF_S)
        taken.setdefault(v, []).append(w)
        hits.append((int(row), float(s), w))
        used.append(s)
        if len(hits) == K:
            break
    return hits


def main():
    vecs, vid, t, queries = load()
    n = len(vecs)
    starts, ends = runs(vid)
    run_of = np.repeat(np.arange(len(starts)), ends - starts)
    # int8 copy: one scale per row (largest |value| -> 127), and the L1 norm of each row's codes for the error bound
    scale = np.abs(vecs).max(axis=1) / 127.0
    codes = np.round(vecs / scale[:, None]).clip(-127, 127).astype(np.int8)
    codes_l1 = np.abs(codes.astype(np.int32)).sum(axis=1)
    out = {"rows": n, "videos": int(len(starts)), "queries": int(len(queries)), "k": K,
           "int8_mb": round(codes.nbytes / 1e6 + scale.nbytes / 1e6, 1), "float32_mb": round(vecs.nbytes / 1e6, 1), "per_query": []}
    for qi, q in enumerate(queries):
        exact = vecs @ q  # float32, the reference
        ref = walk(np.argsort(-exact, kind="stable"), lambda r: exact[r], vid, t, starts, ends, run_of)
        # int8 pass: phrase quantised the same way
        qs = np.abs(q).max() / 127.0
        qc = np.round(q / qs).clip(-127, 127).astype(np.int32)
        t0 = time.perf_counter()
        approx = (codes.astype(np.int32) @ qc).astype(np.float64) * scale * qs
        # |v.q - approx| <= |v - s c|_inf |q|_1 + s |c|_1 |q - qs qc|_inf  (each rounding error is at most half a step)
        bound = (scale / 2) * np.abs(q).sum() + scale * codes_l1 * (qs / 2)
        order8 = np.argsort(-approx, kind="stable")
        m, rounds = 4 * K, 0
        while True:
            rounds += 1
            cand = order8[:m]
            computed = {}

            def score_of(r):
                if r not in computed:
                    computed[r] = vecs[r] @ q
                return computed[r]
            ex = np.array([score_of(r) for r in cand], dtype=np.float32)
            cand_order = cand[np.argsort(-ex, kind="stable")]
            got = walk(cand_order, score_of, vid, t, starts, ends, run_of)
            weakest = min(s for _, s, _ in got) if len(got) == K else -np.inf
            rest = order8[m:]
            # certified when no row outside the candidates can reach the weakest seed: approx + bound < weakest
            certified = len(got) == K and (len(rest) == 0 or float((approx[rest] + bound[rest]).max()) < weakest)
            if certified or m >= n:
                break
            m = min(n, m * 2)
        ms = (time.perf_counter() - t0) * 1e3
        same = [(a[0], a[2]) for a in got] == [(b[0], b[2]) for b in ref]
        out["per_query"].append({"query": qi, "identical": bool(same), "certified": bool(certified), "candidates": int(m),
                                 "rounds": rounds, "float_rows_read": len(computed), "ms_laptop": round(ms, 1),
                                 "max_bound": round(float(bound.max()), 5)})
        print(f"q{qi:02d} identical {same}  certified {certified}  candidates {m:6d}  float rows read {len(computed):6d}  rounds {rounds}")
    pq = out["per_query"]
    out["summary"] = {"identical": sum(p["identical"] for p in pq), "certified": sum(p["certified"] for p in pq),
                      "median_float_rows_read": int(np.median([p["float_rows_read"] for p in pq])),
                      "max_float_rows_read": max(p["float_rows_read"] for p in pq),
                      "median_bytes_read_mb": round((codes.nbytes + scale.nbytes) / 1e6 + np.median([p["float_rows_read"] for p in pq]) * 2048 / 1e6, 1)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "int8-windows.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["summary"]), f"| int8 copy {out['int8_mb']} MB against float32 {out['float32_mb']} MB")


if __name__ == "__main__":
    main()
