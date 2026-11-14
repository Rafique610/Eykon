# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib==3.9.2"]
# ///
"""EYKO-117: turn a phone's `EykonVideo` log into the Head 3 intake tables.

Three commands (run with `uv run src/benchmarks/head3_intake.py ...`; this form reads the inline dependencies above, so `chart` finds matplotlib):

  parse   --log <logcat.txt> --out docs/results/head3 --phone <model> --commit <hash> --scenario S1 --run 1
          [--battery <battery.csv>] [--copy-ms <ms> ...]   (--copy-ms: the harness's file-growth figures, used only if the log has no `copy` line)
          Reads the app's own log lines and APPENDS to <out>/stage_times.csv (one row per stage per video) and
          <out>/run_summary.csv (one row per run). The log may hold one video or a queue of many.
  backfill --db <pulled memories.db> [--video-id <id>] [--stage latest]
          S4: marks one finished video's saved stage as <stage> so the app re-runs only the later stages when it starts.
  chart   --out docs/results/head3 [--scenario S1] [--png <file>]
          One bar chart of the median time per stage from stage_times.csv.

stage_times.csv columns: phone, commit, scenario, run, video_id, video_seconds, stage, ms, frames_in, frames_out, rerun
  rerun is 1 when the same stage appears again for the same video in one log (a back-fill, or a job resumed after its stage was logged). Reruns stay
  in stage_ms_total (the work was done) but are left out of the chart medians, and the run's notes say how many there were.
  split_frames / split_audio are the two parts of the split stage (the log gives both); `link` has no time in the log (blank).
  copy / hash come from the app's `copy` log line (EYKO-71: "copy <id>: <bytes> bytes in <ms> ms (hash <ms> ms)") when the build has it.
  frames_out for small_objects is the number of objects found; for latest it is the number of sightings.
run_summary.csv columns: phone, commit, scenario, run, videos_ready, videos_unfinished (a split line but no `finish ... ready`), video_seconds_total, stage_ms_total,
  work_s_per_video_s (stage time added up, divided by the video's length), wall_ms_estimate, copy_ms, battery_start_pct,
  battery_end_pct, battery_used_pct, max_temp_c, notes
  battery_used_pct only means battery use when the phone was NOT charging; battery.csv has a `plugged` column (AC / USB / Wireless / none)
  and the notes say whether the phone was plugged in.
  wall_ms_estimate = last `finish` time minus (first split line time minus the split's own frames+audio time): an estimate from the
  log, not a stopwatch. The log's clock has no year, so a run that crosses midnight is handled by adding a day.

Log formats accepted: `logcat -v time` ("11-10 01:17:28.485 I/EykonVideo(17657): split <id>: ..."), `-v threadtime`
("11-10 01:17:28.485 17657 17657 I EykonVideo: split <id>: ...") and a console copy ("EykonVideo: split <id>: ...").
"""
import argparse
import csv
import re
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

STAGE_COLUMNS = ["phone", "commit", "scenario", "run", "video_id", "video_seconds", "stage", "ms", "frames_in", "frames_out", "rerun"]
SUMMARY_COLUMNS = ["phone", "commit", "scenario", "run", "videos_ready", "videos_unfinished", "video_seconds_total", "stage_ms_total",
                   "work_s_per_video_s", "wall_ms_estimate", "copy_ms", "battery_start_pct", "battery_end_pct", "battery_used_pct",
                   "max_temp_c", "notes"]
OUTSIDE_THE_TOTAL = ("copy", "hash")  # kept as their own rows and the copy_ms column, but not added into stage_ms_total (EYKO-117 review, 11 Nov)
STAGE_ORDER = ["copy", "hash", "split_frames", "split_audio", "filter", "dedup", "scene", "small_objects", "embed_images", "embed_texts", "link", "latest"]

LINE = re.compile(r"^(?:(?P<stamp>\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\s+)?.*?EykonVideo\s*(?:\(\s*\d+\))?\s*:\s*(?P<stage>\w+) (?P<id>[0-9a-f]{32}):?\s*(?P<rest>.*)$")


def stamp_to_datetime(stamp: str | None, previous: datetime | None) -> datetime | None:
    if not stamp:
        return None
    moment = datetime.strptime(f"2000-{stamp}", "%Y-%m-%d %H:%M:%S.%f")
    while previous is not None and moment < previous - timedelta(seconds=1):
        moment += timedelta(days=1)  # the log has no year; a run across midnight
    return moment


def parse_log(text: str) -> dict:
    """-> {video_id: {"rows": [(stage, ms, in, out)], "seconds": float|None, "ready": bool,
                       "first": datetime|None, "split_ms": int, "finish": datetime|None}}"""
    videos: dict[str, dict] = {}
    previous = None
    for raw in text.splitlines():
        m = LINE.match(raw.strip())
        if not m:
            continue
        stage, vid, rest = m.group("stage"), m.group("id"), m.group("rest")
        moment = stamp_to_datetime(m.group("stamp"), previous)
        previous = moment or previous
        v = videos.setdefault(vid, {"rows": [], "seconds": None, "ready": False, "started": False, "copy_ms": None, "first": None, "split_ms": 0, "finish": None})
        if stage == "copy":  # EYKO-71: "copy <id>: <bytes> bytes in <ms> ms (hash <ms> ms)"; a refused duplicate logs it too, with no split/finish
            s = re.search(r"(\d+) bytes in (\d+) ms(?: \(hash (\d+) ms\))?", rest)
            if s:
                v["copy_ms"] = int(s.group(2))
                v["rows"].append(("copy", int(s.group(2)), None, None))
                if s.group(3) is not None:
                    v["rows"].append(("hash", int(s.group(3)), None, None))
        elif stage == "split":
            s = re.search(r"(\d+) frames in (\d+) ms.*audio ([\d.]+) s in (\d+) ms", rest)
            if s:
                v["started"] = True
                v["rows"] += [("split_frames", int(s.group(2)), None, int(s.group(1))), ("split_audio", int(s.group(4)), None, None)]
                v["seconds"] = float(s.group(3))
                v["split_ms"] = int(s.group(2)) + int(s.group(4))
                v["first"] = v["first"] or moment
        elif stage == "filter":
            s = re.search(r"kept (\d+) of (\d+).* in (\d+) ms", rest)
            if s:
                v["rows"].append(("filter", int(s.group(3)), int(s.group(2)), int(s.group(1))))
        elif stage == "dedup":
            s = re.search(r"kept (\d+) of (\d+).* in (\d+) ms", rest)
            if s:
                v["rows"].append(("dedup", int(s.group(3)), int(s.group(2)), int(s.group(1))))
        elif stage == "scene":
            s = re.search(r"(\d+) frames described.* in (\d+) ms", rest)
            if s:
                v["rows"].append(("scene", int(s.group(2)), int(s.group(1)), int(s.group(1))))
        elif stage == "small_objects":
            s = re.search(r"(\d+) frames looked at, (\d+) found, in (\d+) ms", rest)
            if s:
                v["rows"].append(("small_objects", int(s.group(3)), int(s.group(1)), int(s.group(2))))
        elif stage == "embed_images":
            s = re.search(r"(\d+) vectors stored.* in (\d+) ms", rest)
            if s:
                v["rows"].append(("embed_images", int(s.group(2)), int(s.group(1)), int(s.group(1))))
        elif stage == "embed_texts":
            s = re.search(r"(\d+) texts.* in (\d+) ms", rest)
            if s:
                v["rows"].append(("embed_texts", int(s.group(2)), int(s.group(1)), int(s.group(1))))
        elif stage == "link":
            v["rows"].append(("link", None, None, None))
        elif stage == "latest":
            s = re.search(r"(\d+) sightings.* in (\d+) ms", rest)
            if s:
                v["rows"].append(("latest", int(s.group(2)), None, int(s.group(1))))
        elif stage == "finish":
            v["ready"] = "ready" in rest
            v["finish"] = moment
    return videos


def read_battery(path: Path) -> tuple[int | None, int | None, float | None, set[str] | None]:
    """battery.csv: time,level_pct,temp_c[,plugged]  -> (first level, last level, highest temperature, the `plugged` values seen).
    The last item is None for an older file with no `plugged` column."""
    levels, temps, plugged = [], [], None
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and "plugged" in reader.fieldnames:
            plugged = set()
        for r in reader:
            try:
                levels.append(int(r["level_pct"]))
                temps.append(float(r["temp_c"]))
            except (KeyError, ValueError):
                continue
            if plugged is not None and r.get("plugged"):
                plugged.add(r["plugged"].strip())
    return (levels[0], levels[-1], max(temps), plugged) if levels else (None, None, None, plugged)


def plugged_note(plugged: set[str] | None) -> str:
    """One sentence for the run's notes: battery_used_pct means nothing while the phone charges (EYKO-117 review, 12 Nov)."""
    if plugged is None:
        return ""
    charging = sorted(p for p in plugged if p.lower() != "none")
    if charging:
        return f" PLUGGED IN during the run ({'/'.join(charging)}): battery_used_pct is not battery use."
    return " Not plugged in: battery_used_pct is battery use."


def append_rows(path: Path, columns: list[str], rows: list[dict]) -> None:
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        if new:
            w.writeheader()
        w.writerows(rows)


def cmd_parse(a) -> int:
    videos = parse_log(Path(a.log).read_text(encoding="utf-8", errors="replace"))
    if not videos:
        print("no EykonVideo pipeline lines found in", a.log)
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = {"phone": a.phone, "commit": a.commit, "scenario": a.scenario, "run": a.run}
    stage_rows, total_ms, total_s, ready, failed, reruns = [], 0, 0.0, 0, 0, 0
    starts, finishes = [], []
    for vid, v in videos.items():
        seen: set[str] = set()
        for stage, ms, f_in, f_out in v["rows"]:
            rerun = stage in seen  # the same stage again for the same video in this log
            seen.add(stage)
            reruns += rerun
            stage_rows.append({**base, "video_id": vid, "video_seconds": v["seconds"] or "", "stage": stage, "ms": "" if ms is None else ms,
                               "frames_in": "" if f_in is None else f_in, "frames_out": "" if f_out is None else f_out, "rerun": 1 if rerun else ""})
            if stage not in OUTSIDE_THE_TOTAL:  # the copy happens before the job starts, and the hash time is already inside the copy time
                total_ms += ms or 0
        total_s += v["seconds"] or 0.0
        ready += v["ready"]
        failed += v["started"] and not v["ready"]  # a split line but no "finish ... ready" line: failed or still running. A refused duplicate (copy line only) is not counted
        if v["first"] and v["finish"]:
            starts.append(v["first"] - timedelta(milliseconds=v["split_ms"]))
            finishes.append(v["finish"])
    wall = int((max(finishes) - min(starts)).total_seconds() * 1000) if starts and finishes else ""
    b0 = b1 = peak = plugged = None
    if a.battery and Path(a.battery).exists():
        b0, b1, peak, plugged = read_battery(Path(a.battery))
    notes = ((a.notes or "") + plugged_note(plugged)
             + (f" {reruns} stage record(s) ran more than once (rerun=1 in stage_times.csv; counted in stage_ms_total, left out of the chart)." if reruns else ""))
    from_log = [v["copy_ms"] for v in videos.values() if v["copy_ms"] is not None and v["started"]]
    # the app's own `copy` log line (EYKO-71) wins; the harness's file-growth figures (--copy-ms) are the fallback for older builds
    copy_ms = ";".join(str(x) for x in from_log) if from_log else (";".join(str(x) for x in a.copy_ms) if a.copy_ms else "")
    copy_source = "log" if from_log else ("file growth" if a.copy_ms else "none")
    summary = {**base, "videos_ready": ready, "videos_unfinished": failed, "video_seconds_total": round(total_s, 1), "stage_ms_total": total_ms,
               "work_s_per_video_s": round(total_ms / 1000 / total_s, 2) if total_s else "", "wall_ms_estimate": wall, "copy_ms": copy_ms,
               "battery_start_pct": "" if b0 is None else b0, "battery_end_pct": "" if b1 is None else b1,
               "battery_used_pct": "" if b0 is None else b0 - b1, "max_temp_c": "" if peak is None else peak, "notes": (notes + f" copy_ms source: {copy_source}.").strip()}
    append_rows(out / "stage_times.csv", STAGE_COLUMNS, stage_rows)
    append_rows(out / "run_summary.csv", SUMMARY_COLUMNS, [summary])
    if plugged and any(p.lower() != "none" for p in plugged):
        print("WARNING: the phone was charging during this run, so battery_used_pct is not battery use.")
    print(f"{a.scenario} run {a.run}: {len(videos)} video(s), {ready} ready, {failed} unfinished; stage time added up {total_ms / 1000:.1f} s "
          f"for {total_s:.1f} s of video ({summary['work_s_per_video_s']} s of work per second of video); wall estimate {wall} ms")
    return 0 if failed == 0 else 2


def cmd_backfill(a) -> int:
    """S4: mark ONE finished video's saved stage as <stage> in a pulled memories.db (the app re-queues it on start, MemoryApp.kt back-fill).
    The WAL is checkpointed first so the single .db file holds every row. Rafique's SQL (EYKO-117 card):
      UPDATE jobs SET stage='latest' WHERE status='done' AND video_id='<one video id>';"""
    import sqlite3

    db = Path(a.db)
    con = sqlite3.connect(str(db))
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    vid = a.video_id or (con.execute("SELECT video_id FROM jobs WHERE status = 'done' ORDER BY id DESC LIMIT 1").fetchone() or [None])[0]
    if not vid:
        print("no finished job in the database: nothing to back-fill")
        return 1
    changed = con.execute("UPDATE jobs SET stage = ? WHERE status = 'done' AND video_id = ?", (a.stage, vid)).rowcount
    con.commit()
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    for suffix in ("-wal", "-shm"):  # an empty leftover must not be pushed back next to the edited file
        Path(str(db) + suffix).unlink(missing_ok=True)
    print(f"set the saved stage of video {vid} to '{a.stage}' ({changed} job row changed)")
    return 0 if changed == 1 else 1


def chart_rows(path: Path, scenario: str | None) -> list[dict]:
    """The stage records the chart uses: a time was logged, it is not a rerun, and it belongs to the scenario when one is given."""
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["ms"] != "" and r.get("rerun", "") != "1" and (not scenario or r["scenario"] == scenario)]


def cmd_chart(a) -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = chart_rows(Path(a.out) / "stage_times.csv", a.scenario)
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["stage"], []).append(int(r["ms"]) / 1000)
    stages = [s for s in STAGE_ORDER if s in by] + [s for s in by if s not in STAGE_ORDER]
    medians = [statistics.median(by[s]) for s in stages]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(stages, medians, color="#4c78a8")
    ax.bar_label(bars, labels=[f"{m:.1f}" for m in medians], padding=2)
    ax.set_ylabel("median time per video (s)")
    ax.set_title(f"Time per stage{' (' + a.scenario + ')' if a.scenario else ''}, {len(rows)} stage records")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    png = Path(a.png) if a.png else Path(a.out) / f"stage_medians{'_' + a.scenario if a.scenario else ''}.png"
    fig.savefig(png, dpi=150)
    print("wrote", png)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse")
    p.add_argument("--log", required=True)
    p.add_argument("--out", default="docs/results/head3")
    p.add_argument("--phone", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--battery")
    p.add_argument("--copy-ms", type=int, nargs="*")
    p.add_argument("--notes")
    b = sub.add_parser("backfill")
    b.add_argument("--db", required=True)
    b.add_argument("--video-id")
    b.add_argument("--stage", default="latest")
    c = sub.add_parser("chart")
    c.add_argument("--out", default="docs/results/head3")
    c.add_argument("--scenario")
    c.add_argument("--png")
    a = ap.parse_args()
    return {"parse": cmd_parse, "backfill": cmd_backfill, "chart": cmd_chart}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
