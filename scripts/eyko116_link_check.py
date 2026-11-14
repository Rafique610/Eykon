"""EYKO-116 part 3: the link check on a database pulled from the phone.

The ten rules are copied from android/app/src/main/java/com/eykon/memory/video/VideoLink.kt (RULES); that file is the
source of truth, keep them in step. Every count must be 0 for every video.

Usage:  python -I scripts/eyko116_link_check.py [--adb PATH] [--db FILE] [--label NAME] [--csv FILE]
Without --db it pulls databases/memories.db (+ -wal, -shm) from the phone with `run-as` (the app is debuggable) into a temp folder.
Exit code 0 when every count is 0 and every video is in state ready or processing; 1 otherwise.
"""
import argparse
import csv
import datetime
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

RULES = [
    ("kept frames without a picture hash", "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND f.phash IS NULL"),
    ("kept frames without a scene record", "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND NOT EXISTS (SELECT 1 FROM scene_records s WHERE s.frame_id = f.id)"),
    ("kept frames without an image vector", "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND NOT EXISTS (SELECT 1 FROM image_vec v WHERE v.frame_id = f.id)"),
    ("texts without a text vector", "SELECT COUNT(*) FROM video_texts t WHERE t.video_id = ? AND NOT EXISTS (SELECT 1 FROM text_vec v WHERE v.text_id = t.id)"),
    ("sound windows without a sound vector", "SELECT COUNT(*) FROM audio_windows w WHERE w.video_id = ? AND NOT EXISTS (SELECT 1 FROM audio_vec v WHERE v.window_id = w.id)"),
    ("frames timed outside the video", "SELECT COUNT(*) FROM frames f JOIN videos v ON v.video_id = f.video_id WHERE f.video_id = ? AND (f.t_s < 0 OR f.t_s > v.duration_s + 1)"),
    ("texts timed outside the video", "SELECT COUNT(*) FROM video_texts t JOIN videos v ON v.video_id = t.video_id WHERE t.video_id = ? AND (t.start_s < 0 OR t.end_s < t.start_s OR t.end_s > v.duration_s + 1)"),
    ("sound segments timed outside the video", "SELECT COUNT(*) FROM audio_segments a JOIN videos v ON v.video_id = a.video_id WHERE a.video_id = ? AND (a.start_s < 0 OR a.end_s < a.start_s OR a.end_s > v.duration_s + 1)"),
    ("transcript chunks timed outside the video", "SELECT COUNT(*) FROM transcript_chunks c JOIN videos v ON v.video_id = c.video_id WHERE c.video_id = ? AND (c.start_s < 0 OR c.end_s < c.start_s OR c.end_s > v.duration_s + 1)"),
    ("sound windows timed outside the video", "SELECT COUNT(*) FROM audio_windows w JOIN videos v ON v.video_id = w.video_id WHERE w.video_id = ? AND (w.start_s < 0 OR w.end_s < w.start_s OR w.end_s > v.duration_s + 1)"),
]


def pull(adb: str, folder: Path) -> Path:
    for name in ("memories.db", "memories.db-wal", "memories.db-shm"):
        data = subprocess.run([adb, "exec-out", "run-as", "com.eykon.memory", "cat", f"databases/{name}"], capture_output=True).stdout
        if data:
            (folder / name).write_bytes(data)
    return folder / "memories.db"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default=r"C:\platform-tools\adb.exe")
    ap.add_argument("--db")
    ap.add_argument("--label", default="")
    ap.add_argument("--csv")
    args = ap.parse_args()
    bad = 0
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(args.db) if args.db else pull(args.adb, Path(tmp))
        db = sqlite3.connect(str(path))
        videos = db.execute("SELECT video_id, status, duration_s FROM videos ORDER BY created_at").fetchall()
        print(f"{len(videos)} videos in {path.name}")
        for video_id, status, duration in videos:
            counts = [db.execute(sql, (video_id,)).fetchone()[0] for _, sql in RULES]
            problems = [f"{c} {label}" for (label, _), c in zip(RULES, counts) if c]
            if problems or status not in ("ready", "processing"):
                bad += 1
            print(f"  {video_id[:8]} {status:10} {duration or 0:8.1f}s  " + ("OK: all counts 0" if not problems else "; ".join(problems)))
            rows.append([datetime.datetime.now().isoformat(timespec="seconds"), args.label, video_id, status, duration] + counts)
        for j in db.execute("SELECT video_id, status, stage, attempts, error FROM jobs ORDER BY id").fetchall():
            print(f"  job {j[0][:8]} status={j[1]} stage={j[2]} attempts={j[3]} error={j[4]}")
        db.close()
    if args.csv:
        new = not Path(args.csv).exists()
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["time", "label", "video_id", "status", "duration_s"] + [label for label, _ in RULES])
            w.writerows(rows)
    print("RESULT:", "every count is 0" if not bad else f"{bad} video(s) with a problem")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
