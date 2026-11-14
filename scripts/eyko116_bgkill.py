"""EYKO-116 part 1: the background-kill hold with the adopted vector setup (MAPPED_NATIVE), with every file the card asks for saved.

Usage:  python -I scripts/eyko116_bgkill.py --commit <hash> --out docs/results/vectors/bgkill/infinix-<date>
It checks the job queue is empty, saves `dumpsys meminfo com.eykon.memory` before, runs
OffHeapVectorTest#holdInBackground (mode MAPPED_NATIVE, 100k rows x 3 tables, 300 s), prints OPEN OTHER APPS NOW when the test
says so (you open at least 5 heavy apps yourself), waits for the end, then saves meminfo after, the raw `logcat -d -s EYKO109` and
the test's own output. Never run connectedDebugAndroidTest: it uninstalls the app. Install with `adb install -r` only.
"""
import argparse
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PKG = "com.eykon.memory"


def adb(a, *args, **kw):
    return subprocess.run([a.adb, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", **kw).stdout


def queue_is_empty(a) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("memories.db", "memories.db-wal", "memories.db-shm"):
            data = subprocess.run([a.adb, "exec-out", "run-as", PKG, "cat", f"databases/{name}"], capture_output=True).stdout
            if data:
                (Path(tmp) / name).write_bytes(data)
        db = sqlite3.connect(str(Path(tmp) / "memories.db"))
        jobs = db.execute("SELECT video_id, status, stage FROM jobs").fetchall()
        db.close()
    waiting = [j for j in jobs if j[1] in ("queued", "running")]
    print(f"jobs in the database: {len(jobs)}; not finished: {len(waiting)} {waiting}")
    return not waiting


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default=r"C:\platform-tools\adb.exe")
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--mode", default="MAPPED_NATIVE")
    ap.add_argument("--n", default="100k", help="rows per table, e.g. 20k (HEAP_F32 cannot hold 100k x 3 in the 268 MB heap)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    if not queue_is_empty(a):
        print("STOP: a video job is not finished; it would restart inside the test process (seen in EYKO-111). Let it finish first.")
        return 1
    (out / "device-sheet.txt").write_text(adb(a, "shell", "dumpsys battery") + adb(a, "shell", "df -h /data") + adb(a, "shell", "getprop ro.build.version.release") + adb(a, "shell", "grep MemTotal /proc/meminfo"), encoding="utf-8")
    (out / "meminfo-before.txt").write_text(adb(a, "shell", "dumpsys", "meminfo", PKG), encoding="utf-8")
    adb(a, "logcat", "-G", "16M")
    adb(a, "logcat", "-c")
    cmd = (f"am instrument -w -e class com.eykon.memory.video.OffHeapVectorTest#holdInBackground -e mode {a.mode} -e n {a.n} "
           f"-e seconds {a.seconds} -e commit {a.commit} com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner")
    p = subprocess.Popen([a.adb, "shell", cmd], stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    started = time.time()
    told = False
    while p.poll() is None:
        time.sleep(5)
        log = adb(a, "logcat", "-d", "-s", "EYKO109")
        if not told and "open other apps now" in log:
            print("\n*** OPEN OTHER APPS NOW: at least 5 heavy apps, for the next", a.seconds, "seconds. ***\a\n")
            told = True
        if time.time() - started > a.seconds + 900:
            print("timeout waiting for the test")
            break
    test_out = p.stdout.read() if p.stdout else ""
    (out / "meminfo-after.txt").write_text(adb(a, "shell", "dumpsys", "meminfo", PKG), encoding="utf-8")
    (out / "eyko109-logcat.txt").write_text(adb(a, "logcat", "-d", "-s", "EYKO109"), encoding="utf-8")
    (out / "instrument-output.txt").write_text(test_out, encoding="utf-8")
    # Android's own record of how the process ended (reason, signal, PSS/RSS at the end) and the whole log around it
    (out / "exit-info.txt").write_text(adb(a, "shell", "dumpsys", "activity", "exit-info", PKG), encoding="utf-8")
    (out / "logcat-all-buffers.txt").write_text(adb(a, "logcat", "-d", "-b", "all", "-v", "threadtime"), encoding="utf-8")
    log = (out / "eyko109-logcat.txt").read_text(encoding="utf-8")
    pids = set(re.findall(r"pid (\d+)", log))
    print("pids seen in the log:", pids, "(one pid = not killed)")
    print("test result:", "OK" if "OK (1 test)" in test_out else test_out[-300:])
    for line in log.splitlines():
        if "hold: after" in line:
            print(line[-160:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
