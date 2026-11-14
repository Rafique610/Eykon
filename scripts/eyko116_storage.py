"""EYKO-116 part 2: what the app's data on the phone holds right now, one CSV row per call.

Usage:  python -I scripts/eyko116_storage.py --minutes 15 --label "after clip 3" --csv docs/results/vectors/storage/infinix-<date>-storage.csv
`--minutes` is the total minutes of video added so far. Needs the app installed and debuggable (`run-as`). Sizes are in bytes
(`ls -l`) or KB (`du -sk`) as the column name says. Only sizes are read, never file content.
"""
import argparse
import csv
import datetime
import re
import subprocess
from pathlib import Path

PKG = "com.eykon.memory"


def run_as(adb: str, command: str) -> str:
    return subprocess.run([adb, "shell", f"run-as {PKG} sh -c '{command}'"], capture_output=True, text=True).stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default=r"C:\platform-tools\adb.exe")
    ap.add_argument("--minutes", type=float, required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--csv", required=True)
    a = ap.parse_args()

    def du(path: str) -> int:
        out = run_as(a.adb, f"du -sk {path} 2>/dev/null").split()
        return int(out[0]) if out and out[0].isdigit() else 0

    listing = run_as(a.adb, "ls -l databases")
    sizes = {m.group(2): int(m.group(1)) for m in re.finditer(r"\s(\d+)\s+\d{4}-\d\d-\d\d\s+\d\d:\d\d\s+(\S+)", listing)}
    database = sizes.get("memories.db", 0) + sizes.get("memories.db-wal", 0)
    vectors = sum(v for k, v in sizes.items() if k.startswith("memories.db.") and (k.endswith(".vec") or k.endswith(".ids")))
    videos_kb = du("files/videos")
    mp4_kb = frames_kb = 0
    for vid in run_as(a.adb, "ls files/videos").split():
        mp4_kb += du(f"files/videos/{vid}/{vid}.mp4")
        frames_kb += du(f"files/videos/{vid}/frames")
    row = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"), "label": a.label, "video_minutes_total": a.minutes,
        "database_bytes": database, "vector_files_bytes": vectors, "video_copies_kb": mp4_kb, "frame_files_kb": frames_kb,
        "videos_folder_kb": videos_kb, "other_in_videos_kb": max(0, videos_kb - mp4_kb - frames_kb), "app_data_total_kb": du("."),
    }
    new = not Path(a.csv).exists()
    Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
    with open(a.csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    print(row)


if __name__ == "__main__":
    main()
