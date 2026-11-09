"""EYKO-116 part 3: kill the app in the middle of a pipeline stage, reopen it, and log what the job does.

Usage:  python -I scripts/eyko116_kill.py --stage scene --delay 5 --log docs/results/vectors/crash/infinix-<date>-kill-scene-run1.txt
Add the clip to the app first (it must be processing). The script reads the app's own log (tag EykonVideo). A stage writes its
log line when it ENDS, so the script waits for the line that ends the stage before the one to hit, waits --delay seconds, and runs
`am force-stop com.eykon.memory`. It then reopens the app (launcher intent, the Eykon app only) and keeps reading until the video
reaches "finish ... ready", a failure line shows up, or --wait seconds pass. Everything it saw is written to --log, with times.
Stage order: split, filter, dedup, scene, small_objects, embed_images, embed_texts, link, latest.
"""
import argparse
import datetime
import re
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

ORDER = ["split", "filter", "dedup", "scene", "small_objects", "embed_images", "embed_texts", "link", "latest"]
# `logcat -v time` prints "I/EykonVideo(17657): split <id>: ..."; a hand-copied console prints "EykonVideo: split <id>: ..."
LINE = re.compile(r"EykonVideo\s*(?:\(\s*\d+\))?\s*:\s*(\w+)\s+([0-9a-f]{32})")


def job_row(adb: str) -> str:
    """The job as the database says right after the kill: status, saved stage, attempts (the stage it will resume at)."""
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("memories.db", "memories.db-wal", "memories.db-shm"):
            data = subprocess.run([adb, "exec-out", "run-as", "com.eykon.memory", "cat", f"databases/{name}"], capture_output=True).stdout
            if data:
                (Path(tmp) / name).write_bytes(data)
        db = sqlite3.connect(str(Path(tmp) / "memories.db"))
        rows = db.execute("SELECT video_id, status, stage, attempts FROM jobs").fetchall()
        db.close()
    return "; ".join(f"video {r[0][:8]} status={r[1]} stage={r[2]!r} attempts={r[3]}" for r in rows) or "no job rows"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default=r"C:\platform-tools\adb.exe")
    ap.add_argument("--stage", required=True, choices=ORDER[1:], help="stage to kill the app inside")
    ap.add_argument("--delay", type=float, default=5, help="seconds after the previous stage's end line")
    ap.add_argument("--wait", type=int, default=900, help="seconds to keep watching after the reopen")
    ap.add_argument("--log", required=True)
    ap.add_argument("--replay", help="test without a phone: read EykonVideo lines from this text file and only print what would be done")
    a = ap.parse_args()
    previous = ORDER[ORDER.index(a.stage) - 1]
    out = open(a.log, "w", encoding="utf-8")

    def say(text: str) -> None:
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"{stamp} {text}")
        out.write(f"{stamp} {text}\n")
        out.flush()

    say(f"waiting for the end of '{previous}' to kill inside '{a.stage}' (delay {a.delay}s)")
    if a.replay:
        class _Fake:
            stdout = open(a.replay, encoding="utf-8", errors="replace")
            def terminate(self): pass
        p = _Fake()
    else:
        p = subprocess.Popen([a.adb, "logcat", "-v", "time", "-s", "EykonVideo"], stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    killed = False
    reopened_at = None
    video = None
    try:
        for raw in p.stdout:
            line = raw.rstrip()
            if not line or line.startswith("---"):
                continue
            out.write("   | " + line + "\n")
            m = LINE.search(line)
            stage = m.group(1) if m else None
            if m and video is None:
                video = m.group(2)
            if not killed and stage == previous:
                if a.replay:
                    say(f"[replay] would sleep {a.delay}s, then run: adb shell am force-stop com.eykon.memory, then reopen the app")
                    killed = True
                    continue
                time.sleep(a.delay)
                subprocess.run([a.adb, "shell", "am", "force-stop", "com.eykon.memory"])
                killed = True
                say(f"force-stopped after the '{previous}' line (video {m.group(2)[:8]}), delay {a.delay}s: inside '{a.stage}'")
                time.sleep(3)
                alive = subprocess.run([a.adb, "shell", "pidof", "com.eykon.memory"], capture_output=True, text=True).stdout.strip()
                say(f"app process after the kill: {alive or 'none (killed)'}")
                say("job in the database right after the kill: " + job_row(a.adb))
                subprocess.run([a.adb, "shell", "monkey", "-p", "com.eykon.memory", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
                reopened_at = time.time()
                say("reopened the app")
            if killed and "finish" in line and "ready" in line:
                say("RESULT: the video reached ready after the reopen")
                break
            if killed and re.search(r"fail|error|exception", line, re.I):
                say("note: failure/error line seen after the kill (see log)")
            if reopened_at and time.time() - reopened_at > a.wait:
                say(f"RESULT: no 'ready' within {a.wait}s after the reopen")
                break
    finally:
        p.terminate()
        out.close()


if __name__ == "__main__":
    main()
