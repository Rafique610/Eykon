"""EYKO-91 laptop vector benchmark v2. Run: task vectors-laptop-v2 -- --sources random --sizes 1k,5k

Every (source, size, method) runs in its own fresh process (peak memory only rises within a
process), timing 1 warm-up and then --runs x 20 queries. One CSV row per run, in the phones'
shared format plus recall_at_20, appended to docs/results/vectors/laptop-<date>-sweep[-real].csv.
"""
import argparse
import csv
import datetime
import gc
import json
import os
import re
import resource
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import psutil  # noqa: E402

from src.benchmarks import _vector_sources as vs  # noqa: E402
from src.benchmarks._vector_methods import METHODS  # noqa: E402

HEADER = ("device,android,sqlite_version,commit,date,method,dim,n,run,median_ms,p95_ms,worst_ms,pss_mb,heap_mb,"
          "file_mb,temp_c_start,temp_c_end,battery_pct,source_vectors,note,recall_at_20").split(",")
SUFFIX = {"random": "sweep", "real": "sweep-real", "varied": "sweep-varied"}  # names the figure script globs
K, QUERIES = 20, 20


def pss_mb() -> int:
    return round(psutil.Process().memory_full_info().pss / 2**20)


def cpu_temp():
    temps = psutil.sensors_temperatures().get("coretemp", [])
    return next((t.current for t in temps if t.label.startswith("Package")), temps[0].current if temps else None)


def cpu_name() -> str:
    text = Path("/proc/cpuinfo").read_text() if Path("/proc/cpuinfo").exists() else ""
    found = re.search(r"model name\s*:\s*(.*)", text)
    model = found.group(1) if found else "unknown cpu"
    short = re.search(r"(i\d-\w+|Ryzen \d \w+)", model)
    return short.group(1) if short else model.strip()


def commit() -> str:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, cwd=ROOT).stdout
    return head + ("-dirty" if dirty.strip() else "")


def stats(times):
    s = sorted(times)
    return s[len(s) // 2], s[ceil(0.95 * len(s)) - 1], s[-1]


def run_one(source: str, n: int, name: str, runs: int, dim: int) -> list:
    """Child process: build one method at one size, time it, return its CSV rows (as dicts)."""
    method = METHODS[name]
    before = pss_mb()
    vecs, qs = vs.vectors(source, n, dim), vs.queries(source, QUERIES + 1, dim)
    exact_scores = qs @ vecs.T  # the float32 reference for recall, kept after vecs is dropped
    with tempfile.TemporaryDirectory(prefix="eyko91_") as workdir:
        start = time.perf_counter()
        extra = method.build(vecs, workdir)
        build_s = time.perf_counter() - start
        del vecs
        gc.collect()
        held = pss_mb()
        file_mb = method.file_mb()
        temp_start = cpu_temp()
        method.search(qs[0], K)  # warm-up, not timed
        timed = []
        for _ in range(runs):
            times, recalls = [], []
            for q, scores in zip(qs[1:], exact_scores[1:]):
                t = time.perf_counter()
                ids = method.search(q, K)
                times.append((time.perf_counter() - t) * 1000)
                recalls.append(vs.recall_from_scores(scores, ids, K))
            timed.append((times, float(np.mean(recalls))))
        temp_end = cpu_temp()
    battery = psutil.sensors_battery()
    note = {"build_s": f"{build_s:.1f}", **extra, "pss_before_mb": before, "pss_after_mb": held,
            "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
            "charger": "in" if battery and battery.power_plugged else "out", "threads": os.cpu_count()}
    rows = []
    for run, (times, recall) in enumerate(timed, 1):
        median, p95, worst = stats(times)
        rows.append({"method": name, "dim": dim, "n": n, "run": run, "median_ms": f"{median:.2f}", "p95_ms": f"{p95:.2f}",
                     "worst_ms": f"{worst:.2f}", "pss_mb": held, "file_mb": f"{file_mb:.1f}" if file_mb else "",
                     "temp_c_start": f"{temp_start:.1f}" if temp_start else "", "temp_c_end": f"{temp_end:.1f}" if temp_end else "",
                     "battery_pct": round(battery.percent) if battery else "", "recall_at_20": f"{recall:.4f}",
                     "note": "; ".join(f"{k}={v}" for k, v in note.items())})
    if method.exact and min(r for _, r in timed) < 1.0:
        sys.exit(f"BUG: {name} is exact but recall@20 = {min(r for _, r in timed):.4f} at n={n} ({source})")
    return rows


def size(text: str) -> int:
    return int(float(text[:-1]) * 1000) if text.lower().endswith("k") else int(text)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sources", default="random,real")
    p.add_argument("--sizes", default="1k,5k,20k,50k,100k,300k")
    p.add_argument("--methods", default=",".join(METHODS))
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--dim", type=int, default=512)
    p.add_argument("--out", default=str(ROOT / "docs/results/vectors"))
    p.add_argument("--device", default=f"laptop {cpu_name()}")
    p.add_argument("--one", nargs=3, metavar=("SOURCE", "N", "METHOD"), help=argparse.SUPPRESS)
    a = p.parse_args()
    if a.one:
        print(json.dumps(run_one(a.one[0], int(a.one[1]), a.one[2], a.runs, a.dim)))
        return

    unknown = set(a.methods.split(",")) - set(METHODS)
    if unknown:
        sys.exit(f"unknown methods: {', '.join(sorted(unknown))}")
    date = datetime.date.today().isoformat()
    fixed = {"device": a.device, "android": "", "sqlite_version": sqlite3.sqlite_version, "commit": commit(),
             "date": date, "heap_mb": ""}
    print(f"{a.device} · python {sys.version.split()[0]} · numpy {np.__version__} · sqlite {sqlite3.sqlite_version} · {fixed['commit']}")
    for source in a.sources.split(","):
        out = Path(a.out) / f"laptop-{date}-{SUFFIX[source]}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        new = not out.exists()
        with out.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADER)
            if new:
                writer.writeheader()
            for n in map(size, a.sizes.split(",")):
                for name in a.methods.split(","):
                    if METHODS[name].max_n and n > METHODS[name].max_n:
                        print(f"skip {source} n={n} {name}: above {METHODS[name].max_n}")
                        continue
                    start = time.perf_counter()
                    child = subprocess.run([sys.executable, __file__, "--one", source, str(n), name, "--runs", str(a.runs),
                                            "--dim", str(a.dim)], capture_output=True, text=True)
                    if child.returncode:
                        sys.exit(f"{source} n={n} {name} failed:\n{child.stderr.strip()}")
                    rows = json.loads(child.stdout.strip().splitlines()[-1])
                    for r in rows:
                        writer.writerow({**fixed, "source_vectors": vs.label(source), **r})
                    f.flush()
                    medians = [float(r["median_ms"]) for r in rows]
                    print(f"{source:>6} n={n:>6} {name:<24} median {statistics.median(medians):9.2f} ms  "
                          f"recall {rows[0]['recall_at_20']}  pss {rows[0]['pss_mb']} MB  ({time.perf_counter() - start:.0f} s)")
    print(f"written to {Path(a.out)}")


if __name__ == "__main__":
    main()
