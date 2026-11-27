"""Hypothesis 5 (decision re-check, 26 Nov): two ideas for object sightings, both tested here. Laptop. Run:

    uv run --no-project --with numpy python -I src/benchmarks/recheck_sightings.py

5a  Same-object rule. Today (VideoLatest.kt): same name and crop cosine >= 0.87. Alternatives that use time as well:
    "same clip within T s counts as the same object, else the crop rule", and "a scene-sized crop (side >= S px) within the
    same clip is the same object". Data: the phone's 54 identified crops (EYKO-15) with the identities a person checked
    (EYKO-72: docs/results/latest/crop-identity-2026-10-13-reviewed.csv); frame numbers are at 3 a second. No boxes are saved,
    so a rule using box overlap (tracking) cannot be tested on this data.
5b  Storage. A sighting row holds its 2 KB crop vector, about 4.1 kB on disk at 4 KB pages. Would a separate table help?
    20,000 rows of the app's object_sightings shape, 4 KB and 16 KB pages, vector inside the row against a side table.
Writes docs/results/recheck-sightings/recheck-sightings.json.
"""
import csv
import json
import os
import random
import sqlite3
import struct
import tempfile
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/results/recheck-sightings"


def rules():
    crops = {c["crop"]: c for c in json.load(open(ROOT / "docs/results/latest/pixel9proxl-object-crops-2026-10-13.json"))["crops"]}
    objects = {r["crop"]: r["object"] for r in csv.DictReader(open(ROOT / "docs/results/latest/crop-identity-2026-10-13-reviewed.csv"))}
    pairs = []
    for a, b in combinations(sorted(objects), 2):
        ca, cb = crops[a], crops[b]
        if ca["label"] != cb["label"] or (ca["clip"], ca["frame_no"]) == (cb["clip"], cb["frame_no"]):
            continue
        dt = abs(int(ca["frame_no"]) - int(cb["frame_no"])) / 3.0 if ca["clip"] == cb["clip"] else float("inf")
        pairs.append((objects[a] == objects[b], float(np.dot(ca["vector"], cb["vector"])), dt, max(int(ca["side"]), int(cb["side"]))))
    same = [p for p in pairs if p[0]]
    diff = [p for p in pairs if not p[0]]

    def ev(rule):
        miss, merged = sum(not rule(p) for p in same), sum(rule(p) for p in diff)
        return {"same_missed": miss, "different_merged": merged, "wrong": miss + merged}
    out = {"crops": len(objects), "same_pairs": len(same), "different_pairs": len(diff),
           "different_pairs_within_10_s": sum(p[2] <= 10 for p in diff), "rules": {"app: cosine >= 0.87": ev(lambda p: p[1] >= 0.87)}}
    for t in (2, 5, 10, 30):
        out["rules"][f"same clip within {t} s, else cosine 0.87"] = ev(lambda p, t=t: p[2] <= t or p[1] >= 0.87)
    for side in (400, 480):
        out["rules"][f"scene-sized crop (side >= {side} px) in the same clip, else cosine 0.87"] = \
            ev(lambda p, s=side: (p[3] >= s and p[2] != float("inf")) or p[1] >= 0.87)
    return out


def storage(n=20000):
    rnd = random.Random(5)
    rows = [(f"lab{rnd.randrange(60)}", rnd.randrange(1, 10**6), "v" * 36, "2026-11-26T10:00:00.000Z", "kitchen",
             struct.pack("<512f", *[rnd.uniform(-.1, .1) for _ in range(512)])) for _ in range(n)]
    out = {}
    with tempfile.TemporaryDirectory() as d:
        for page in (4096, 16384):
            for inside in (True, False):
                path = os.path.join(d, "s.db")
                if os.path.exists(path):
                    os.remove(path)
                c = sqlite3.connect(path)
                c.execute(f"PRAGMA page_size={page}")
                emb = "embedding BLOB NOT NULL," if inside else ""
                c.execute("CREATE TABLE object_sightings (id INTEGER PRIMARY KEY, label TEXT NOT NULL, frame_id INTEGER NOT NULL, video_id TEXT NOT NULL,"
                          f" seen_at TEXT NOT NULL, place TEXT, {emb} is_latest INTEGER NOT NULL DEFAULT 1, superseded_by INTEGER)")
                c.execute("CREATE INDEX object_sightings_label ON object_sightings(label, is_latest)")
                if not inside:
                    c.execute("CREATE TABLE sighting_vec (sighting_id INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
                for i, r in enumerate(rows, 1):
                    if inside:
                        c.execute("INSERT INTO object_sightings (id,label,frame_id,video_id,seen_at,place,embedding) VALUES (?,?,?,?,?,?,?)", (i,) + r)
                    else:
                        c.execute("INSERT INTO object_sightings (id,label,frame_id,video_id,seen_at,place) VALUES (?,?,?,?,?,?)", (i,) + r[:5])
                        c.execute("INSERT INTO sighting_vec VALUES (?,?)", (i, r[5]))
                c.commit()
                c.close()
                out[f"page {page}, vector {'inside the row' if inside else 'in a side table'}"] = round(os.path.getsize(path) / n)
    return {"rows": n, "bytes_per_sighting": out}


if __name__ == "__main__":
    result = {"5a_same_object_rules": rules(), "5b_storage": storage()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "recheck-sightings.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))
