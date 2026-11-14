"""EYKO-119: force-stop the Eykon app inside one stage on a real phone, reopen it, and compare the result with a clean run.

Run with the repo's Python (`python -I scripts/eyko119_force_stop.py ...`). Needs adb and a phone with the debug build (run-as).
Never runs connectedDebugAndroidTest. The app's own database is backed up first and put back at the end.

  backup  --dir D                 stop the app, copy memories.db (+ wal, shm, vector files) and the list of video folders to D
  run     --label L [--kill-after STAGE --delay S] --out O
                                   wait for you to add a clip in the Video tab (the app logs "copy <id>"), then
                                   - without --kill-after: wait until the video is ready (the clean run);
                                   - with it: force-stop S seconds after the log line of STAGE (so the kill lands in the next stage),
                                     save the job's stage from the database, reopen the app, wait until the video is ready.
                                   Writes O/L.json (counts, link check, saved stage, which stages ran in the new process) and O/L-logcat.txt.
  compare --out O                 table of every O/*.json against the clean run; exit 1 when a number differs
  restore --dir D                 put the database files back and delete the video folders added since the backup
"""
import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PKG = "com.eykon.memory"
STAGES = ["split", "filter", "dedup", "scene", "small_objects", "embed_images", "embed_texts", "link", "latest", "finish"]
LINE = re.compile(r"^\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}\s+(\d+)\s+\d+ I EykonVideo: (\w+) ([0-9a-f]{32}):? ?(.*)$")
# the ten counts VideoLink.kt must find at zero (copied from RULES there)
LINK_RULES = {
    "kept frames without a picture hash": "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND f.phash IS NULL",
    "kept frames without a scene record": "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND NOT EXISTS (SELECT 1 FROM scene_records s WHERE s.frame_id = f.id)",
    "kept frames without an image vector": "SELECT COUNT(*) FROM frames f WHERE f.video_id = ? AND f.kept = 1 AND NOT EXISTS (SELECT 1 FROM image_vec v WHERE v.frame_id = f.id)",
    "texts without a text vector": "SELECT COUNT(*) FROM video_texts t WHERE t.video_id = ? AND NOT EXISTS (SELECT 1 FROM text_vec v WHERE v.text_id = t.id)",
    "sound windows without a sound vector": "SELECT COUNT(*) FROM audio_windows w WHERE w.video_id = ? AND NOT EXISTS (SELECT 1 FROM audio_vec v WHERE v.window_id = w.id)",
    "frames timed outside the video": "SELECT COUNT(*) FROM frames f JOIN videos v ON v.video_id = f.video_id WHERE f.video_id = ? AND (f.t_s < 0 OR f.t_s > v.duration_s + 1)",
    "texts timed outside the video": "SELECT COUNT(*) FROM video_texts t JOIN videos v ON v.video_id = t.video_id WHERE t.video_id = ? AND (t.start_s < 0 OR t.end_s < t.start_s OR t.end_s > v.duration_s + 1)",
    "sound segments timed outside the video": "SELECT COUNT(*) FROM audio_segments a JOIN videos v ON v.video_id = a.video_id WHERE a.video_id = ? AND (a.start_s < 0 OR a.end_s < a.start_s OR a.end_s > v.duration_s + 1)",
    "transcript chunks timed outside the video": "SELECT COUNT(*) FROM transcript_chunks c JOIN videos v ON v.video_id = c.video_id WHERE c.video_id = ? AND (c.start_s < 0 OR c.end_s < c.start_s OR c.end_s > v.duration_s + 1)",
    "sound windows timed outside the video": "SELECT COUNT(*) FROM audio_windows w JOIN videos v ON v.video_id = w.video_id WHERE w.video_id = ? AND (w.start_s < 0 OR w.end_s < w.start_s OR w.end_s > v.duration_s + 1)",
}

ADB = "adb"
SERIAL = None


def adb(*args: str, binary: bool = False, check: bool = True):
    cmd = [ADB] + (["-s", SERIAL] if SERIAL else []) + list(args)
    r = subprocess.run(cmd, capture_output=True)
    if check and r.returncode != 0:
        sys.exit(f"adb {' '.join(args)} failed: {r.stderr.decode(errors='replace')[:300]}")
    return r.stdout if binary else r.stdout.decode("utf-8", errors="replace")


def run_as_cat(path: str) -> bytes:
    return adb("exec-out", "run-as", PKG, "cat", path, binary=True)


def db_files() -> list[str]:
    names = adb("shell", f"run-as {PKG} ls databases").split()
    return sorted(n for n in names if n.startswith("memories.db"))


def video_folders() -> list[str]:
    return sorted(adb("shell", f"run-as {PKG} ls files/videos").split())


def force_stop() -> None:
    adb("shell", "am", "force-stop", PKG)


def pull_db(dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    names = db_files()
    for n in names:
        (dest / n).write_bytes(run_as_cat(f"databases/{n}"))
    return names


def log_lines() -> list[tuple[int, str, str, str]]:
    text = adb("logcat", "-d", "-v", "threadtime", "-s", "EykonVideo")
    return [(int(m.group(1)), m.group(2), m.group(3), m.group(4)) for m in (LINE.match(x.strip()) for x in text.splitlines()) if m]


def wait_for(test, timeout: float, poll: float = 0.25):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        found = test(log_lines())
        if found:
            return found
        time.sleep(poll)
    return None


def metrics(db_dir: Path, vid: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        for f in db_dir.glob("memories.db*"):
            if f.suffix not in (".vec", ".ids"):
                shutil.copy(f, Path(tmp) / f.name)
        con = sqlite3.connect(Path(tmp) / "memories.db")

        def one(sql, *a):
            row = con.execute(sql, a).fetchone()
            return row[0] if row else None

        job = con.execute("SELECT status, stage, attempts, error FROM jobs WHERE video_id = ?", (vid,)).fetchone()
        captions = [r[0] for r in con.execute("SELECT s.caption FROM scene_records s JOIN frames f ON f.id = s.frame_id WHERE f.video_id = ? ORDER BY f.frame_no", (vid,))]
        out = {
            "video_status": one("SELECT status FROM videos WHERE video_id = ?", vid),
            "job_status": job[0] if job else None, "job_stage": job[1] if job else None, "job_attempts": job[2] if job else None, "job_error": job[3] if job else None,
            "frames_total": one("SELECT COUNT(*) FROM frames WHERE video_id = ?", vid),
            "frames_kept": one("SELECT COUNT(*) FROM frames WHERE video_id = ? AND kept = 1", vid),
            "scene_records": one("SELECT COUNT(*) FROM scene_records s JOIN frames f ON f.id = s.frame_id WHERE f.video_id = ?", vid),
            "video_texts": one("SELECT COUNT(*) FROM video_texts WHERE video_id = ?", vid),
            "image_vec": one("SELECT COUNT(*) FROM image_vec v JOIN frames f ON f.id = v.frame_id WHERE f.video_id = ?", vid),
            "text_vec": one("SELECT COUNT(*) FROM text_vec v JOIN video_texts t ON t.id = v.text_id WHERE t.video_id = ?", vid),
            "sightings": one("SELECT COUNT(*) FROM object_sightings WHERE video_id = ?", vid),
            "sightings_latest": one("SELECT COUNT(*) FROM object_sightings WHERE video_id = ? AND is_latest = 1", vid),
            "captions_sha256": hashlib.sha256("\n".join(captions).encode()).hexdigest()[:16],
            "link_counts": {label: one(sql, vid) for label, sql in LINK_RULES.items()},
        }
        con.close()
        return out


def cmd_backup(a) -> None:
    force_stop()
    d = Path(a.dir)
    names = pull_db(d)
    folders = video_folders()
    (d / "folders.txt").write_text("\n".join(folders), encoding="utf-8")
    print(f"backed up {len(names)} files {names} and {len(folders)} video folders to {d}")


def cmd_restore(a) -> None:
    d = Path(a.dir)
    force_stop()
    keep = set((d / "folders.txt").read_text(encoding="utf-8").split())
    saved = {p.name for p in d.iterdir() if p.name.startswith("memories.db")}
    for n in db_files():
        if n not in saved:
            adb("shell", f"run-as {PKG} rm databases/{n}")
    for n in sorted(saved):
        adb("push", str(d / n), f"/data/local/tmp/eyko119-{n}")
        adb("shell", f"run-as {PKG} sh -c 'cat > databases/{n}' < /data/local/tmp/eyko119-{n}")
        adb("shell", f"rm /data/local/tmp/eyko119-{n}")
    removed = [f for f in video_folders() if f not in keep]
    for f in removed:
        adb("shell", f"run-as {PKG} rm -rf files/videos/{f}")
    same = all(run_as_cat(f"databases/{n}") == (d / n).read_bytes() for n in saved)
    print(f"restored {sorted(saved)}; removed {len(removed)} new video folders {removed}; files now identical to the backup: {same}")


def cmd_run(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    adb("logcat", "-c")
    print(f"[{a.label}] ready. In the app: Video tab, add the clip now." + (f" I will force-stop {a.delay} s after the '{a.kill_after}' line." if a.kill_after else " Clean run: no kill."), flush=True)
    first = wait_for(lambda ls: next(((v, s) for _, s, v, _ in ls if s == "copy"), None), timeout=1500)
    if not first:
        sys.exit("no 'copy' line within 25 minutes: no clip was added")
    vid = first[0]
    print(f"[{a.label}] clip added: video {vid}", flush=True)
    result = {"label": a.label, "video_id": vid, "kill_after": a.kill_after, "delay_s": a.delay}
    if a.kill_after:
        seen = wait_for(lambda ls: next(((p, s) for p, s, v, _ in ls if v == vid and s == a.kill_after), None), timeout=240)
        if not seen:
            sys.exit(f"no '{a.kill_after}' line for {vid} within 4 minutes (a refused duplicate? the clip not accepted?)")
        time.sleep(a.delay)
        before = [s for _, s, v, _ in log_lines() if v == vid and s in STAGES]
        force_stop()
        result["stages_logged_before_kill"] = before
        killed_pid = seen[0]
        pulled = pull_db(out / f"{a.label}-after-kill")
        m = metrics(out / f"{a.label}-after-kill", vid)
        result["at_kill"] = {k: m[k] for k in ("video_status", "job_status", "job_stage", "job_attempts", "frames_total", "scene_records", "video_texts", "sightings")}
        print(f"[{a.label}] force-stopped after: {before[-1] if before else '-'}; saved stage in the database: '{m['job_stage']}', job {m['job_status']}, video {m['video_status']}", flush=True)
        adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
        print(f"[{a.label}] app reopened; waiting for ready", flush=True)
    done = wait_for(lambda ls: next((p for p, s, v, r in ls if v == vid and s == "finish" and "ready" in r), None), timeout=720, poll=1.0)
    lines = [l for l in log_lines() if l[2] == vid]
    pids = []
    for p, *_ in lines:
        if p not in pids:
            pids.append(p)
    result["processes"] = len(pids)
    result["stages_in_new_process"] = [s for p, s, _, _ in lines if p != pids[0] and s in STAGES] if len(pids) > 1 else []
    result["reached_ready"] = bool(done)
    (out / f"{a.label}-logcat.txt").write_text(adb("logcat", "-d", "-v", "threadtime", "-s", "EykonVideo"), encoding="utf-8")
    pull_db(out / a.label)
    result.update(metrics(out / a.label, vid))
    (out / f"{a.label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[{a.label}] {'READY' if done else 'NOT READY (timeout)'}; resumed stages: {result['stages_in_new_process']}; link counts all zero: {all(v == 0 for v in result['link_counts'].values())}", flush=True)
    shutil.rmtree(out / a.label, ignore_errors=True)  # the pulled databases hold other videos of the person; keep only the numbers
    shutil.rmtree(out / f"{a.label}-after-kill", ignore_errors=True)


def cmd_compare(a) -> None:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(a.out).glob("*.json"))]
    clean = next((r for r in runs if not r["kill_after"]), None)
    if not clean:
        sys.exit("no clean run (a run without --kill-after) in " + a.out)
    keys = ["video_status", "job_status", "frames_total", "frames_kept", "scene_records", "video_texts", "image_vec", "text_vec", "sightings", "sightings_latest", "captions_sha256"]
    bad = 0
    print(f"{'run':8} {'killed after':14} {'saved':14} {'resumed at':14} " + " ".join(f"{k[:9]:>9}" for k in keys) + "  link=0  same")
    for r in runs:
        same = all(r[k] == clean[k] for k in keys) and all(v == 0 for v in r["link_counts"].values()) and r["reached_ready"]
        bad += not same
        resumed = r["stages_in_new_process"][0] if r["stages_in_new_process"] else "-"
        saved = (r.get("at_kill") or {}).get("job_stage", "-")
        print(f"{r['label']:8} {str(r['kill_after'] or '-'):14} {str(saved):14} {resumed:14} " + " ".join(f"{str(r[k])[:9]:>9}" for k in keys) + f"  {all(v == 0 for v in r['link_counts'].values())!s:6}  {same}")
    sys.exit(1 if bad else 0)


def main() -> None:
    global ADB, SERIAL
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adb", default="adb")
    ap.add_argument("--serial")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup"); b.add_argument("--dir", required=True)
    r = sub.add_parser("restore"); r.add_argument("--dir", required=True)
    u = sub.add_parser("run"); u.add_argument("--label", required=True); u.add_argument("--kill-after"); u.add_argument("--delay", type=float, default=2.0); u.add_argument("--out", required=True)
    c = sub.add_parser("compare"); c.add_argument("--out", required=True)
    a = ap.parse_args()
    ADB, SERIAL = a.adb, a.serial
    {"backup": cmd_backup, "restore": cmd_restore, "run": cmd_run, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    main()
