"""EYKO-116 part 2: take a storage reading every time a video finishes, while a queue of clips is processed.

Usage:  python -u -I scripts/eyko116_storage_watch.py --csv docs/results/vectors/storage/infinix-<date>-storage.csv --log <raw log file> [--videos 4]
Zara adds the clips (5, 10, 15, 30 min) one after another in the app; the app works through the queue. This script reads the app's own
log (`logcat -s EykonVideo`). On every `split` line it learns the video's length (the audio length in seconds); on every
`finish ... ready` line it runs scripts/eyko116_storage.py with the TOTAL minutes finished so far. Every 2 minutes it checks the
job table (`failed` stops the watch and says so) and notes battery level and temperature. Only sizes and the job table are read.
"""
import argparse
import datetime
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

PKG = "com.eykon.memory"
LINE = re.compile(r"EykonVideo\s*(?:\(\s*\d+\))?\s*:\s*(\w+)\s+([0-9a-f]{32}):?\s*(.*)")


def jobs(adb: str) -> list[tuple]:
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("memories.db", "memories.db-wal", "memories.db-shm"):
            data = subprocess.run([adb, "exec-out", "run-as", PKG, "cat", f"databases/{name}"], capture_output=True).stdout
            if data:
                (Path(tmp) / name).write_bytes(data)
        db = sqlite3.connect(str(Path(tmp) / "memories.db"))
        rows = db.execute("SELECT video_id, status, stage, attempts, error FROM jobs ORDER BY id").fetchall()
        db.close()
    return rows


def battery(adb: str) -> str:
    text = subprocess.run([adb, "shell", "dumpsys", "battery"], capture_output=True, text=True).stdout
    level = re.search(r"level:\s*(\d+)", text)
    temp = re.search(r"temperature:\s*(\d+)", text)
    return f"battery {level.group(1) if level else '?'} %, {int(temp.group(1)) / 10 if temp else '?'} C"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default=r"C:\platform-tools\adb.exe")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--videos", type=int, default=4)
    ap.add_argument("--timeout-min", type=int, default=240)
    a = ap.parse_args()
    log = open(a.log, "w", encoding="utf-8")
    subprocess.run([a.adb, "logcat", "-G", "16M"], capture_output=True)
    subprocess.run([a.adb, "logcat", "-c"], capture_output=True)
    state = {"stop": False, "failed": False}

    def say(text: str) -> None:
        line = f"{datetime.datetime.now().strftime('%H:%M:%S')} {text}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    def checker() -> None:
        while not state["stop"]:
            for _ in range(120):
                if state["stop"]:
                    return
                time.sleep(1)
            try:
                rows = jobs(a.adb)
                bad = [r for r in rows if r[1] == "failed"]
                say(f"check: {[(r[0][:8], r[1], r[2]) for r in rows]}; {battery(a.adb)}")
                if bad:
                    say(f"FAILED job: {[(r[0][:8], r[2], r[3], r[4]) for r in bad]}")
                    state["failed"] = True
                    state["stop"] = True
            except Exception as e:  # a missed check is not fatal
                say(f"check failed: {e}")

    threading.Thread(target=checker, daemon=True).start()
    p = subprocess.Popen([a.adb, "logcat", "-v", "time", "-s", "EykonVideo"], stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    seconds: dict[str, float] = {}
    done_s = 0.0
    done = 0
    started = time.time()
    say(f"watching for {a.videos} video(s); {battery(a.adb)}")
    try:
        for raw in p.stdout:
            line = raw.rstrip()
            if not line or line.startswith("---"):
                continue
            log.write("   | " + line + "\n")
            m = LINE.search(line)
            if m:
                stage, vid, rest = m.group(1), m.group(2), m.group(3)
                s = re.search(r"audio ([\d.]+) s", rest)
                if stage == "split" and s:
                    seconds[vid] = float(s.group(1))
                    say(f"video {vid[:8]}: split done, {seconds[vid]:.1f} s long")
                if stage == "finish" and "ready" in rest:
                    done += 1
                    done_s += seconds.get(vid, 0.0)
                    say(f"video {vid[:8]} ready ({done} of {a.videos}); total finished {done_s / 60:.1f} min: taking the storage reading")
                    r = subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("eyko116_storage.py")), "--adb", a.adb, "--minutes",
                                        f"{done_s / 60:.2f}", "--label", f"after video {done} ({seconds.get(vid, 0.0):.0f} s)", "--csv", a.csv],
                                       capture_output=True, text=True)
                    say("reading: " + (r.stdout.strip() or r.stderr.strip())[:400])
                    if done >= a.videos:
                        say("ALL DONE")
                        break
            if state["stop"]:
                break
            if time.time() - started > a.timeout_min * 60:
                say("TIMEOUT")
                break
    finally:
        state["stop"] = True
        p.terminate()
        log.close()
    return 1 if state["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
