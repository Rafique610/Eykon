# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib==3.9.2"]
# ///
"""EYKO-117: turn a phone's `EykonVideo` log into the Head 3 intake tables.

Two commands (run with `uv run python src/benchmarks/head3_intake.py ...`):

  parse   --log <logcat.txt> --out docs/results/head3 --phone <model> --commit <hash> --scenario S1 --run 1
          [--battery <battery.csv>] [--copy-ms <ms> ...]
          Reads the app's own log lines and APPENDS to <out>/stage_times.csv (one row per stage per video) and
          <out>/run_summary.csv (one row per run). The log may hold one video or a queue of many.
  chart   --out docs/results/head3 [--scenario S1] [--png <file>]
          One bar chart of the median time per stage from stage_times.csv.

stage_times.csv columns: phone, commit, scenario, run, video_id, video_seconds, stage, ms, frames_in, frames_out
  split_frames / split_audio are the two parts of the split stage (the log gives both); `link` has no time in the log (blank).
  frames_out for small_objects is the number of objects found; for latest it is the number of sightings.
run_summary.csv columns: phone, commit, scenario, run, videos_ready, videos_unfinished (a split line but no `finish ... ready`), video_seconds_total, stage_ms_total,
  work_s_per_video_s (stage time added up, divided by the video's length), wall_ms_estimate, copy_ms, battery_start_pct,
  battery_end_pct, battery_used_pct, max_temp_c, notes
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

STAGE_COLUMNS = ["phone", "commit", "scenario", "run", "video_id", "video_seconds", "stage", "ms", "frames_in", "frames_out"]
SUMMARY_COLUMNS = ["phone", "commit", "scenario", "run", "videos_ready", "videos_unfinished", "video_seconds_total", "stage_ms_total",
                   "work_s_per_video_s", "wall_ms_estimate", "copy_ms", "battery_start_pct", "battery_end_pct", "battery_used_pct",
                   "max_temp_c", "notes"]
STAGE_ORDER = ["split_frames", "split_audio", "filter", "dedup", "scene", "small_objects", "embed_images", "embed_texts", "link", "latest"]

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
        v = videos.setdefault(vid, {"rows": [], "seconds": None, "ready": False, "first": None, "split_ms": 0, "finish": None})
        if stage == "split":
            s = re.search(r"(\d+) frames in (\d+) ms.*audio ([\d.]+) s in (\d+) ms", rest)
            if s:
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


def read_battery(path: Path) -> tuple[int | None, int | None, float | None]:
    """battery.csv: time,level_pct,temp_c  -> (first level, last level, highest temperature)."""
    levels, temps = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                levels.append(int(r["level_pct"]))
                temps.append(float(r["temp_c"]))
            except (KeyError, ValueError):
                continue
    return (levels[0], levels[-1], max(temps)) if levels else (None, None, None)


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
    stage_rows, total_ms, total_s, ready, failed = [], 0, 0.0, 0, 0
    starts, finishes = [], []
    for vid, v in videos.items():
        for stage, ms, f_in, f_out in v["rows"]:
            stage_rows.append({**base, "video_id": vid, "video_seconds": v["seconds"] or "", "stage": stage, "ms": "" if ms is None else ms,
                               "frames_in": "" if f_in is None else f_in, "frames_out": "" if f_out is None else f_out})
            total_ms += ms or 0
        total_s += v["seconds"] or 0.0
        ready += v["ready"]
        failed += not v["ready"]  # started (a split line) but no "finish ... ready" line: the job failed or was still running
        if v["first"] and v["finish"]:
            starts.append(v["first"] - timedelta(milliseconds=v["split_ms"]))
            finishes.append(v["finish"])
    wall = int((max(finishes) - min(starts)).total_seconds() * 1000) if starts and finishes else ""
    b0 = b1 = peak = None
    if a.battery and Path(a.battery).exists():
        b0, b1, peak = read_battery(Path(a.battery))
    copy_ms = ";".join(str(x) for x in a.copy_ms) if a.copy_ms else ""
    summary = {**base, "videos_ready": ready, "videos_unfinished": failed, "video_seconds_total": round(total_s, 1), "stage_ms_total": total_ms,
               "work_s_per_video_s": round(total_ms / 1000 / total_s, 2) if total_s else "", "wall_ms_estimate": wall, "copy_ms": copy_ms,
               "battery_start_pct": "" if b0 is None else b0, "battery_end_pct": "" if b1 is None else b1,
               "battery_used_pct": "" if b0 is None else b0 - b1, "max_temp_c": "" if peak is None else peak, "notes": a.notes or ""}
    append_rows(out / "stage_times.csv", STAGE_COLUMNS, stage_rows)
    append_rows(out / "run_summary.csv", SUMMARY_COLUMNS, [summary])
    print(f"{a.scenario} run {a.run}: {len(videos)} video(s), {ready} ready, {failed} unfinished; stage time added up {total_ms / 1000:.1f} s "
          f"for {total_s:.1f} s of video ({summary['work_s_per_video_s']} s of work per second of video); wall estimate {wall} ms")
    return 0 if failed == 0 else 2


def cmd_chart(a) -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with open(Path(a.out) / "stage_times.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["ms"] != "" and (not a.scenario or r["scenario"] == a.scenario)]
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
    c = sub.add_parser("chart")
    c.add_argument("--out", default="docs/results/head3")
    c.add_argument("--scenario")
    c.add_argument("--png")
    a = ap.parse_args()
    return cmd_parse(a) if a.cmd == "parse" else cmd_chart(a)


if __name__ == "__main__":
    sys.exit(main())
