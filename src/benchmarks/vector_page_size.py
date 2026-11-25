"""EYKO-167: does a larger SQLite page size stop the vector tables wasting half their space? Laptop part. Run: task page-size

The app's database (one design: src/video_memory/schema.py, copied on the phone) stores each vector as a float32 BLOB row.
A 512-number vector is 2,048 bytes, so with 4 KB pages only one row fits a page. This measures, on the real table design
with real MobileCLIP vectors, at several page sizes:
  E1  bytes a row for every table, in a library filled in our measured proportions (per kept frame: 17 frame rows,
      1 caption, 1 text vector, 5.4 object sightings, each with a 512-number crop vector);
  E2  option (a), a new database made at 16 KB: file size, insert time, the full read that rebuilds the search copy,
      the MAX(id) check, and the vectors read back bit for bit;
  E3  option (b), an existing 4 KB database in WAL mode (as Room uses on the phone) converted with VACUUM;
  E4  whether a new database still takes a page size after WAL is switched on (where the app would have to set it).
Test databases go in data/eyko167/ (git-ignored) and are deleted. Results: docs/results/page-size/page-size.json.
"""

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "data/eyko167"
OUT = ROOT / "docs/results/page-size"
IMAGES = ROOT / "data/eyko91_coco/images_512.f32"  # 100,000 real MobileCLIP-S2 image vectors (EYKO-91)
TEXTS = ROOT / "android/app/src/androidTest/assets/vectors/own_text_384.f32"  # 90 real BGE caption vectors
CAPTIONS = ROOT / "data/eyko91_coco/captions_val2017.json"  # real short captions, about our captions' length

# Per kept frame, from our runs (see docs/results/2026-11-21-vector-growth-estimate.md and the files named there)
FRAME_ROWS_PER_KEPT = round(3 * 60 / 10.6)  # 3 sampled frames a second, 10.6 kept a minute (24 Ego4D clips) -> 17
SIGHTINGS_PER_KEPT = 5.4  # kit clip 1: 54 sightings from 10 kept frames (head3 runs)
KEPT_PER_VIDEO = 53  # a 5-minute video at 10.6 kept a minute: one transaction per video, as the app's stages write
PAGES = [4096, 8192, 16384, 32768, 65536]


def schema_ddl():
    """The DDL string from src/video_memory/schema.py, read as text (importing it would open the app database)."""
    text = (ROOT / "src/video_memory/schema.py").read_text(encoding="utf-8")
    start = text.index('DDL = """') + len('DDL = """')
    return text[start:text.index('"""', start)]


DDL = schema_ddl()
IMG = np.fromfile(IMAGES, dtype=np.float32).reshape(-1, 512)
TXT = np.fromfile(TEXTS, dtype=np.float32).reshape(-1, 384)
CAPS = [a["caption"].strip() for a in json.load(open(CAPTIONS, encoding="utf-8"))["annotations"]]


def open_db(path, page, journal):
    con = sqlite3.connect(path, isolation_level=None)
    con.execute(f"PRAGMA page_size={page}")  # before any table: takes effect when the file is first written
    con.execute(f"PRAGMA journal_mode={journal}")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def fill(con, kept, image_only=False):
    """Insert `kept` kept frames, one transaction per video, with every table in the measured proportions."""
    if not image_only:
        con.executescript(DDL)
    else:
        con.execute("CREATE TABLE image_vec (frame_id INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
    start, frame_id, sighting = time.perf_counter(), 0, 0
    for v0 in range(0, kept, KEPT_PER_VIDEO):
        vid = f"{v0:032x}"
        con.execute("BEGIN")
        if not image_only:
            con.execute("INSERT INTO videos VALUES (?, ?, '2026-11-01T10:00:00Z', 300, NULL, NULL, 'ready', '2026-11-01T10:00:00Z', ?, ?, ?)",
                        (vid, f"/data/videos/{vid}/{vid}.mp4", "f" * 64, f"content://media/picker/0/{v0}", f"PXL_{v0}.mp4"))
        for k in range(v0, min(v0 + KEPT_PER_VIDEO, kept)):
            if image_only:
                con.execute("INSERT INTO image_vec VALUES (?, ?)", (k + 1, IMG[k % len(IMG)].tobytes()))
                continue
            for j in range(FRAME_ROWS_PER_KEPT):  # the kept frame is the last of its run of sampled frames
                frame_id += 1
                kept_flag = j == FRAME_ROWS_PER_KEPT - 1
                con.execute("INSERT INTO frames VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (frame_id, vid, frame_id, frame_id / 3, f"{vid}/frames/{frame_id:06d}.jpg", f"{frame_id * 2654435761 % 2**64:016x}",
                             int(kept_flag), None if kept_flag else f"duplicate of frame {frame_id - 1}"))
            caption = CAPS[k % len(CAPS)]
            con.execute("INSERT INTO scene_records VALUES (?, ?, ?, ?, ?, ?, 'A')",
                        (frame_id, json.dumps([{"label": w, "conf": 0.81, "box": [12.5, 40.0, 210.25, 318.75]} for w in caption.split()[:5]]),
                         "walking", "a kitchen", 1, caption))
            con.execute("INSERT INTO image_vec VALUES (?, ?)", (frame_id, IMG[k % len(IMG)].tobytes()))
            con.execute("INSERT INTO video_texts (video_id, source, ref_id, start_s, end_s, text) VALUES (?, 'caption', ?, ?, ?, ?)",
                        (vid, frame_id, frame_id / 3, frame_id / 3, caption))
            con.execute("INSERT INTO text_vec VALUES (last_insert_rowid(), ?)", (TXT[k % len(TXT)].tobytes(),))
            n = int(SIGHTINGS_PER_KEPT * (k + 1)) - int(SIGHTINGS_PER_KEPT * k)
            for _ in range(n):
                sighting += 1
                con.execute("INSERT INTO object_sightings (id, label, frame_id, video_id, seen_at, place, embedding, is_latest, superseded_by) "
                            "VALUES (?, ?, ?, ?, '2026-11-01T10:02:13.333Z', 'a kitchen', ?, 1, NULL)",
                            (sighting, caption.split()[0].lower(), frame_id, vid, IMG[(k * 7 + sighting) % len(IMG)].tobytes()))
        con.execute("COMMIT")
    return time.perf_counter() - start


def table_bytes(con):
    """dbstat: bytes on disk per table, its indexes and (for the keyword index) its shadow tables."""
    owner = {r[0]: r[1] for r in con.execute("SELECT name, tbl_name FROM sqlite_master")}
    out = {}
    for name, size in con.execute("SELECT name, SUM(pgsize) FROM dbstat GROUP BY name"):
        t = owner.get(name, name)
        t = "video_texts_fts" if t.startswith("video_texts_fts") else t
        out[t] = out.get(t, 0) + size
    return out


def rows(con):
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
            ("frames", "scene_records", "image_vec", "video_texts", "text_vec", "object_sightings")}


def image_digest(con):
    h = hashlib.sha256()
    for (blob,) in con.execute("SELECT embedding FROM image_vec ORDER BY frame_id"):
        h.update(blob)
    return h.hexdigest()


def expected_digest(kept):
    h = hashlib.sha256()
    for k in range(kept):
        h.update(IMG[k % len(IMG)].tobytes())
    return h.hexdigest()


def timed(fn, repeat=3):
    best = float("inf")
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best


def reads(con):
    """The two reads the app does on image_vec: MAX(id) on every search, the full read when the search copy is rebuilt."""
    return {"max_id_ms": round(timed(lambda: con.execute("SELECT IFNULL(MAX(frame_id), 0) FROM image_vec").fetchone(), 20) * 1e3, 3),
            "full_read_s": round(timed(lambda: sum(1 for _ in con.execute("SELECT frame_id, embedding FROM image_vec ORDER BY frame_id"))), 3)}


def fresh(name):
    path = WORK / name
    for suffix in ("", "-wal", "-shm", "-journal"):
        Path(f"{path}{suffix}").unlink(missing_ok=True)
    return path


def e1_library(kept=20_000):
    result = {}
    for page in PAGES:
        path = fresh(f"lib-{page}.db")
        con = open_db(path, page, "delete")
        insert_s = fill(con, kept)
        tb, rc = table_bytes(con), rows(con)
        result[page] = {"page_size": con.execute("PRAGMA page_size").fetchone()[0], "file_bytes": os.path.getsize(path),
                        "insert_s": round(insert_s, 2), "rows": rc, "table_bytes": tb,
                        "bytes_per_row": {t: round(tb[t] / rc[t], 1) for t in rc if rc[t]},
                        "per_kept_frame_bytes": round(os.path.getsize(path) / kept), **reads(con),
                        "image_vec_identical": image_digest(con) == expected_digest_lib(con)}
        print(page, result[page]["file_bytes"] / 1e6, "MB", result[page]["bytes_per_row"])
        con.close()
        fresh(f"lib-{page}.db")
    return result


def expected_digest_lib(con):
    """In the library the k-th kept frame's vector is IMG[k]; image_vec is ordered by frame_id, which grows with k."""
    n = con.execute("SELECT COUNT(*) FROM image_vec").fetchone()[0]
    return expected_digest(n)


def e2_image_only(kept=100_000):
    result = {}
    for page in (4096, 16384):
        path = fresh(f"img-{page}.db")
        con = open_db(path, page, "wal")
        insert_s = fill(con, kept, image_only=True)
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        result[page] = {"page_size": con.execute("PRAGMA page_size").fetchone()[0], "file_bytes": os.path.getsize(path),
                        "bytes_per_row": round(os.path.getsize(path) / kept, 1), "insert_s": round(insert_s, 2), **reads(con),
                        "identical": image_digest(con) == expected_digest(kept)}
        print("100k image", page, result[page])
        con.close()
        if page == 16384:
            fresh(f"img-{page}.db")
    return result


def e3_migrate(kept=100_000):
    """The 4 KB WAL database from E2 converted in place, as the app would on an existing install."""
    path = WORK / "img-4096.db"
    con = sqlite3.connect(path, isolation_level=None)
    before = {"page_size": con.execute("PRAGMA page_size").fetchone()[0], "journal": con.execute("PRAGMA journal_mode").fetchone()[0],
              "file_bytes": os.path.getsize(path)}
    con.execute("PRAGMA page_size=16384")  # 1. try it in WAL mode
    t = time.perf_counter()
    con.execute("VACUUM")
    in_wal = {"vacuum_s": round(time.perf_counter() - t, 2), "page_size_after": con.execute("PRAGMA page_size").fetchone()[0]}
    con.execute("PRAGMA journal_mode=DELETE")  # 2. leave WAL, change, VACUUM, back to WAL
    con.execute("PRAGMA page_size=16384")
    t = time.perf_counter()
    con.execute("VACUUM")
    vacuum_s = time.perf_counter() - t
    con.execute("PRAGMA journal_mode=WAL")
    after = {"page_size": con.execute("PRAGMA page_size").fetchone()[0], "journal": con.execute("PRAGMA journal_mode").fetchone()[0],
             "file_bytes": os.path.getsize(path), "vacuum_s": round(vacuum_s, 2), "integrity": con.execute("PRAGMA integrity_check").fetchone()[0],
             "identical": image_digest(con) == expected_digest(kept), "max_frame_id": con.execute("SELECT MAX(frame_id) FROM image_vec").fetchone()[0]}
    con.close()
    fresh("img-4096.db")
    print("migrate", before, in_wal, after)
    return {"before": before, "vacuum_while_wal": in_wal, "after_leaving_wal": after}


def e4_order():
    """A new, empty database: does the page size still apply if WAL is switched on first (Android turns WAL on at open)?"""
    out = {}
    for order in ("page_then_wal", "wal_then_page"):
        path = fresh(f"order-{order}.db")
        con = sqlite3.connect(path, isolation_level=None)
        steps = ["PRAGMA page_size=16384", "PRAGMA journal_mode=WAL"] if order == "page_then_wal" else ["PRAGMA journal_mode=WAL", "PRAGMA page_size=16384"]
        for s in steps:
            con.execute(s)
        con.execute("CREATE TABLE t (x)")
        out[order] = con.execute("PRAGMA page_size").fetchone()[0]
        con.close()
        fresh(f"order-{order}.db")
    print("order", out)
    return out


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"sqlite": sqlite3.sqlite_version, "vectors": {"image": str(IMAGES.relative_to(ROOT)), "text": str(TEXTS.relative_to(ROOT))},
              "per_kept_frame": {"frame_rows": FRAME_ROWS_PER_KEPT, "sightings": SIGHTINGS_PER_KEPT, "kept_per_video": KEPT_PER_VIDEO},
              "e4_order": e4_order(), "e1_library_20k": e1_library(), "e2_image_100k": e2_image_only(), "e3_migrate_100k": e3_migrate()}
    (OUT / "page-size.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("wrote docs/results/page-size/page-size.json")
