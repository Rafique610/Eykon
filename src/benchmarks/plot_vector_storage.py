"""EYKO-97: the seven vector-storage graphs, redrawn from every CSV in docs/results/vectors/. Run: task vectors-plots

Reads every *.csv under docs/results/vectors/ (subfolders too, never plots/). Files in the shared format (header starts
with device,android,sqlite_version,...) feed graphs 1-4; the storage logs (time,label,video_minutes_total,...) feed graph 5.
A new phone or a rerun shows up on the next run without code changes. Graphs 6 and 7 also need what the CSV columns do not
hold: which condition a run was (cool, hot, low battery) and which code version it timed. They take those from the file
names listed in CONDITIONS and CAPACITY_RUNS below, so a new run of the same kind is picked up when it follows the naming.

Writes PNG and SVG to docs/results/vectors/plots/ and prints every file it used or skipped.
Colour follows the device in every graph (A32 blue, Pixel orange, Infinix green, laptop violet; validated palette from
the Head 2 figures). Where one graph needs many methods, each device gets its own panel and the method gets the colour.
Points are the median over runs of each run's median; error bars run up to the median of the runs' p95.
No pass line is drawn at 200 ms: that target has no source (dropped 8 Nov, EYKO-101). Graphs 1 and 7 mark
100 / 200 / 500 ms as labelled assumptions instead.
"""
import csv
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs/results/vectors"
OUT = DATA / "plots"
SHARED = "device,android,sqlite_version,commit,date,method,dim,n,run,median_ms"
STORAGE = "time,label,video_minutes_total,database_bytes"

DEVICES = {  # short name, colour, marker; the order is the order of panels and bars
    "laptop": ("Laptop i5-10310U", "#6250d6", "D"),
    "Pixel": ("Pixel 9 Pro XL", "#eb6834", "s"),
    "Infinix": ("Infinix X670", "#1baf7a", "^"),
    "A32": ("Samsung A32", "#2a78d6", "o"),
}
SPARE = ["#e87ba4", "#eda100", "#008300"]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
HEAP_LIMIT_MB = 268
BUDGETS_MS = [100, 200, 500]  # assumptions, not sourced limits (EYKO-101)
KEPT_PER_HOUR = 13.4 * 60  # kept frames (one image vector each) per hour of video: Ego4D Pixel run, 372 in 27.8 min (Head 8)
SIZES = [1_000, 5_000, 20_000, 50_000, 100_000, 300_000]

# Graph 1 and 4: which method is "the app's exact search" on each kind of device, in order of preference.
SAME_TEST = {"laptop": ["blob_memory_numpy_1t"], "phone": ["blob_memory_fast"]}
# Graph 6: condition = the first pattern in the file name that matches. Files that match none are not drawn in graph 6.
CONDITIONS = [  # (pattern in the file name, label); the first match wins, so specific patterns come first
    ("plugged-control", "cable (control)"), ("eyko115-speed", "cable"), ("sweep-real", "cable"),
    ("eyko111-warm", "warm, battery"), ("eyko111-hot2", "hot, battery"), ("eyko111-hot-", "hot, battery (spoiled run)"),
    ("eyko111-lowbat-nosaver", "low battery, saver off"), ("eyko111-lowbat2", "low battery, saver on (run 2)"),
    ("eyko111-lowbat-", "low battery, saver on (run 1)"),
    ("-cool", "cool, battery"), ("-hot", "hot, battery"), ("-lowbat", "low battery"),
]
# Graph 7: runs of the app's search as it is now (MAPPED_NATIVE after EYKO-115, no COUNT(*)), the clean run per phone.
# EYKO-114's mapped run still had the COUNT(*) check (565 ms at 100k), so it must not be used.
CAPACITY_RUNS = {"A32": "*eyko111-hot2-*", "Pixel": "*eyko111-lowbat-nosaver-*"}


def device_of(name: str) -> str:
    if name.startswith("laptop"):
        return "laptop"
    for key, words in (("A32", "SM-A325F"), ("Pixel", "Pixel 9 Pro XL"), ("Infinix", "Infinix X670")):
        if words in name:
            return key
    return name


def style(dev: str):
    if dev in DEVICES:
        return DEVICES[dev]
    return dev, SPARE[hash(dev) % len(SPARE)], "v"


def read_all():
    """Every CSV under DATA, split into shared-format rows and storage logs. Prints what was used and skipped."""
    rows, storage = [], []
    for path in sorted(DATA.rglob("*.csv")):
        if OUT in path.parents:
            continue
        rel = path.relative_to(DATA)
        with path.open(encoding="utf-8") as f:
            head = f.readline().strip()
            f.seek(0)
            if head.startswith(SHARED):
                got = [dict(r, file=str(rel), dev=device_of(r["device"])) for r in csv.DictReader(f)]
                rows += got
                print(f"read  {rel} ({len(got)} rows)")
            elif head.startswith(STORAGE):
                storage.append((rel, list(csv.DictReader(f))))
                print(f"read  {rel} (storage log)")
            else:
                print(f"skip  {rel} (not a vector or storage format: {head[:40]}...)")
    return rows, storage


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def note(row) -> dict:
    return dict(p.strip().split("=", 1) for p in row.get("note", "").split(";") if "=" in p)


def run_of(file: str) -> str:
    """Files of one run share a name up to a trailing -YYYYMMDD-HHMM (some phone tests write one file per size)."""
    return re.sub(r"-\d{8}-\d{4}$", "", str(Path(file).with_suffix("")))


def series(rows, dev, method, column="median_ms"):
    """{n: (median, p95)} for one device and method, from the one run that best represents it:
    real vectors first, then the most sizes, then the newest date. Within a run, a later file replaces an earlier
    one for the same size. Returns (points, run name)."""
    runs = defaultdict(list)
    for r in rows:
        if r["dev"] == dev and r["method"] == method and num(r[column]) is not None:
            runs[run_of(r["file"])].append(r)
    if not runs:
        return {}, None

    def rank(item):
        name, rs = item
        return (rs[0]["source_vectors"].startswith("real"), len({r["n"] for r in rs}), rs[0]["date"], name)

    name, rs = max(runs.items(), key=rank)
    latest = {}
    for r in rs:
        latest[int(r["n"])] = max(latest.get(int(r["n"]), ""), r["file"])
    by = defaultdict(list)
    for r in rs:
        if r["file"] == latest[int(r["n"])]:
            by[int(r["n"])].append(r)
    points = {}
    for n, group in sorted(by.items()):
        med = statistics.median(num(r[column]) for r in group)
        p95 = [num(r.get("p95_ms")) for r in group if num(r.get("p95_ms")) is not None] if column == "median_ms" else []
        points[n] = (med, statistics.median(p95) if p95 else med)
    return points, name


def frame(ax, xlabel="Vectors in the table (512 numbers each)", ylabel="", logx=True):
    if logx:
        ax.set_xscale("log")
        ax.set_xticks(SIZES, ["1k", "5k", "20k", "50k", "100k", "300k"])
        ax.minorticks_off()
    ax.set_xlabel(xlabel, color=MUTED, fontsize=8)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=8)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=7.5)


def save(fig, name, title, subtitle):
    import textwrap
    w, h = fig.get_size_inches()
    lines = textwrap.wrap(subtitle, width=int(w * 15))
    top = 1 - (0.42 + 0.17 * len(lines)) / h  # title and subtitle get their own band, measured in inches
    fig.text(0.01, 1 - 0.1 / h, title, ha="left", va="top", fontsize=11, color=INK, fontweight="bold")
    fig.text(0.01, 1 - 0.36 / h, "\n".join(lines), ha="left", va="top", fontsize=8, color=MUTED, linespacing=1.4)
    fig.tight_layout(rect=(0, 0, 1, top))
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=170, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote plots/{name}.png and .svg")


def budget_lines(ax, x0):
    for b in BUDGETS_MS:
        ax.axhline(b, color=MUTED, linewidth=0.8, linestyle=(0, (4, 3)), zorder=1)
        ax.annotate(f"{b} ms (assumed)", (x0, b), xytext=(2, 2), textcoords="offset points", fontsize=6.5, color=MUTED)


# ---------------------------------------------------------------- graph 1
def graph_time(rows):
    """Search time against size: one panel per device, one line per method (the main graph)."""
    devs = [d for d in DEVICES if any(r["dev"] == d for r in rows)] + sorted({r["dev"] for r in rows} - set(DEVICES))
    timed = {(r["dev"], r["method"]) for r in rows
             if num(r["median_ms"]) is not None and not r["method"].startswith(("memory", "app_"))}
    methods = sorted({m for _, m in timed})
    palette = plt.get_cmap("tab10").colors
    fig, panels = plt.subplots(1, len(devs), figsize=(5.2 * len(devs), 7.4), sharey=True)
    for ax, dev in zip(panels, devs):
        label, dev_colour, _ = style(dev)
        for i, m in enumerate([m for m in methods if (dev, m) in timed]):
            pts, _ = series(rows, dev, m)
            ns = list(pts)
            med = [pts[n][0] for n in ns]
            up = [max(pts[n][1] - pts[n][0], 0) for n in ns]
            ax.errorbar(ns, med, yerr=[[0] * len(ns), up], color=palette[i % 10], marker="o", markersize=3.5, linewidth=1.5,
                        linestyle=["-", (0, (4, 2)), (0, (1, 1))][i // 10], capsize=2, label=m)
        ax.set_yscale("log")
        budget_lines(ax, 1_000)
        frame(ax, ylabel="ms per search, median (bar: p95), log" if ax is panels[0] else "")
        ax.set_xlim(700, 400_000)
        ax.set_title(label, color=dev_colour, fontsize=10, loc="left", fontweight="bold")
        ax.legend(frameon=False, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    save(fig, "1-search-time-vs-size", "1 · Search time against table size, every method on every device",
         "One panel per device; colours name methods within a panel. Per device and method, the run with real vectors, "
         "the most sizes and the newest date. Grey dashed lines: assumed budgets, not pass marks.")


# ---------------------------------------------------------------- graph 2
def graph_memory(rows):
    """PSS against size: one table (the speed sweeps), three tables (the old Java array, which runs out), and the app now."""
    devs = [d for d in DEVICES if any(r["dev"] == d for r in rows)]
    fig, panels = plt.subplots(1, len(devs), figsize=(4.6 * len(devs), 4.4), sharey=True)
    for ax, dev in zip(panels, devs):
        label, colour, marker = style(dev)
        laptop = dev == "laptop"
        one, _ = series(rows, dev, SAME_TEST["laptop" if laptop else "phone"][0], "pss_mb")
        if one:
            ax.plot(list(one), [v[0] for v in one.values()], color=colour, marker=marker, linewidth=1.8, markersize=5,
                    linestyle=(0, (1, 2)), label="1 table in a numpy array (speed sweep)" if laptop
                    else "1 table in a Java array (speed sweep)")
            if laptop:
                n, v = list(one.items())[-1]
                ax.annotate(f"{v[0]:.0f} MB at {n // 1000}k\n(no 3-table test, no Java heap)", (n, v[0]), xytext=(-6, -4),
                            textcoords="offset points", ha="right", va="top", fontsize=6.5, color=INK)
        three = sorted((int(r["n"]), num(r["pss_mb"]), note(r).get("tables_loaded", "")) for r in rows
                       if r["dev"] == dev and r["method"] == "memory_all_tables" and num(r["pss_mb"]) is not None)
        if three:
            ax.plot([n for n, _, _ in three], [p for _, p, _ in three], color=colour, marker=marker, linewidth=1.8,
                    markersize=5, label="3 tables in Java arrays (old way)")
            for n, p, loaded in three:
                if not loaded.startswith("3"):
                    ax.annotate(f"only {loaded[0]} of 3 fit", (n, p), xytext=(4, -10), textcoords="offset points",
                                fontsize=6.5, color=INK)
        mapped = sorted((int(r["n"]), num(r["pss_mb"]), num(r["heap_mb"])) for r in rows
                        if r["dev"] == dev and r["method"] == "memory_offheap_mapped_native" and num(r["pss_mb"]) is not None)
        if mapped:
            ax.plot([n for n, _, _ in mapped], [p for _, p, _ in mapped], color=colour, marker=marker, linewidth=2.2,
                    markersize=6, markerfacecolor="white", label="3 tables, mapped file + NEON (the app now)")
            for n, p, heap in mapped:
                ax.annotate(f"Java heap {heap:.0f} MB", (n, p), xytext=(-4, 6), textcoords="offset points", ha="right",
                            fontsize=6.5, color=INK)
        if not laptop:
            ax.axhline(HEAP_LIMIT_MB, color=MUTED, linewidth=0.8, linestyle=(0, (4, 3)))
            ax.annotate(f"Java heap limit {HEAP_LIMIT_MB} MB (not a PSS limit)", (1_000, HEAP_LIMIT_MB), xytext=(2, 3),
                        textcoords="offset points", fontsize=6.5, color=MUTED)
        frame(ax, ylabel="Process memory, PSS (MB)" if ax is panels[0] else "")
        ax.set_xlim(700, 400_000 if laptop else 150_000)
        ax.set_title(label, color=colour, fontsize=10, loc="left", fontweight="bold")
        ax.legend(frameon=False, fontsize=6.5, loc="upper left")
    save(fig, "2-memory-vs-size", "2 · Memory (PSS) against table size: 1 table, 3 tables, and the app's mapped setup, laptop and phones",
         "No run held exactly 2 tables: the 3-table test records how many fit before the Java array ran out of memory. "
         "The mapped setup's pages count in PSS but not in the Java heap.")


# ---------------------------------------------------------------- graph 3
def graph_file_size(rows):
    """Database file size against size: BLOB table against sqlite-vec, measured, per device."""
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    families = [("blob_", "BLOB table (the app's layout)", "-"), ("sqlite_vec", "sqlite-vec vec0", (0, (5, 2)))]
    for dev in [d for d in DEVICES] + sorted({r["dev"] for r in rows} - set(DEVICES)):
        label, colour, marker = style(dev)
        for prefix, fam, ls in families:
            by = defaultdict(list)
            for r in rows:
                kind = "int8" if "int8" in r["method"] or "i8" in r["method"] else "f32"
                if r["dev"] == dev and r["method"].startswith(prefix) and kind == "f32" and num(r["file_mb"]):
                    by[int(r["n"])].append(num(r["file_mb"]))
            if by:
                ns = sorted(by)
                ax.plot(ns, [statistics.median(by[n]) for n in ns], color=colour, marker=marker, linestyle=ls,
                        linewidth=1.8, markersize=4.5, label=f"{label}: {fam}")
    ns = SIZES
    ax.plot(ns, [n * 2048 / 1e6 for n in ns], color=INK, linewidth=1, linestyle=(0, (1, 2)),
            label="the float32 vectors themselves (n × 2,048 B)")
    ax.set_yscale("log")
    frame(ax, ylabel="Database file, MB (log)")
    ax.set_xlim(700, 400_000)
    ax.legend(frameon=False, fontsize=6.5, loc="upper left")
    save(fig, "3-file-size-vs-size", "3 · Database file size: BLOB table against sqlite-vec (float32)",
         "Measured file sizes from every run. The BLOB table is about twice the vectors: SQLite's 4 KB page holds one "
         "512-number row (EYKO-167).")


# ---------------------------------------------------------------- graph 4
def graph_devices(rows):
    """The same exact search on every device: bars, log y."""
    picks = []
    for dev in [d for d in DEVICES] + sorted({r["dev"] for r in rows} - set(DEVICES)):
        for m in SAME_TEST["laptop" if dev == "laptop" else "phone"]:
            pts, name = series(rows, dev, m)
            if pts:
                picks.append((dev, m, pts, name))
                print(f"graph 4: {dev} {m} from {name}")
                break
    sizes = [n for n in [5_000, 20_000, 50_000, 100_000] if all(n in p for _, _, p, _ in picks)]
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    width = 0.8 / len(picks)
    for i, (dev, m, pts, name) in enumerate(picks):
        label, colour, _ = style(dev)
        xs = [k + (i - (len(picks) - 1) / 2) * width for k in range(len(sizes))]
        med = [pts[n][0] for n in sizes]
        up = [max(pts[n][1] - pts[n][0], 0) for n in sizes]
        ax.bar(xs, med, width * 0.9, color=colour, yerr=[[0] * len(sizes), up], ecolor=MUTED, capsize=2, zorder=2,
               label=f"{label} ({m}, {Path(name).stem})")
        for x, y in zip(xs, med):
            ax.annotate(f"{y:.0f}" if y >= 10 else f"{y:.1f}", (x, y), xytext=(0, 2), textcoords="offset points",
                        ha="center", fontsize=6.5, color=INK)
    ax.set_yscale("log")
    frame(ax, ylabel="ms per search, median (bar: p95), log", logx=False)
    ax.set_xticks(range(len(sizes)), [f"{n // 1000}k" for n in sizes])
    ax.legend(frameon=False, fontsize=6.5, loc="upper left")
    save(fig, "4-same-test-devices", "4 · The same exact search on the laptop and every phone",
         "Phones: the fast loop (blob_memory_fast); laptop: numpy, one thread. Runs differ in day and charger (file in the legend). "
         "Exact search time does not depend on the vectors (B3).")


# ---------------------------------------------------------------- graph 5
def graph_storage(storage):
    """Storage against minutes of video, from the storage logs: database, frame files, total app data."""
    fig, panels = plt.subplots(1, len(storage), figsize=(5.2 * len(storage), 4.2), sharey=True)
    panels = panels if len(storage) > 1 else [panels]
    parts = [("database_bytes", 1e6, "database", "#2a78d6"), ("frame_files_kb", 1e3 / 1.024, "frame files", "#eb6834"),
             ("vector_files_bytes", 1e6, "vector files (.vec)", "#1baf7a"), ("app_data_total_kb", 1e3 / 1.024, "total app data", INK)]
    for ax, (rel, log) in zip(panels, storage):
        mins = [num(r["video_minutes_total"]) for r in log]
        for column, div, label, colour in parts:
            vals = [num(r[column]) / div for r in log]
            if any(vals):
                ax.plot(mins, [max(v, 0.01) for v in vals], color=colour, marker="o", markersize=4, linewidth=1.8, label=label)
        last = log[-1]
        per_hour = (num(last["app_data_total_kb"]) - num(log[0]["app_data_total_kb"])) / 1e3 * 1.024 / num(last["video_minutes_total"]) * 60
        ax.annotate(f"total growth ≈ {per_hour:,.0f} MB per hour", (mins[-1], num(last["app_data_total_kb"]) / 1e3 * 1.024),
                    xytext=(-4, 6), textcoords="offset points", ha="right", fontsize=7, color=INK)
        ax.set_yscale("log")
        frame(ax, xlabel="Minutes of video processed", ylabel="MB (log)" if ax is panels[0] else "", logx=False)
        ax.set_title(str(rel), color=INK, fontsize=8.5, loc="left")
        ax.legend(frameon=False, fontsize=6.5, loc="lower right")
    save(fig, "5-storage-per-hour", "5 · Storage as video is processed: database, frame files, total (Infinix, EYKO-116)",
         "These runs copied every video (before EYKO-126), so the total is mostly the copies. Since 13 Nov the app reads "
         "videos in place: about 126 MB per hour of camera video (Pixel, no CSV; 2026-11-13-read-from-gallery.md).")


# ---------------------------------------------------------------- graph 6
def condition_of(file: str):
    for pattern, label in CONDITIONS:
        if pattern in Path(file).name:
            return label
    return None


def graph_heat(rows):
    """Cool, hot and low battery: median ms at 20k and 100k, per device and method, from the condition runs."""
    groups = defaultdict(lambda: defaultdict(list))  # (dev, method) -> condition -> rows
    for r in rows:
        cond = condition_of(r["file"])
        if cond and r["dev"] != "laptop" and r["method"] in ("blob_memory_fast", "offheap_mapped_native") \
                and int(r["n"]) in (20_000, 100_000) and num(r["median_ms"]) is not None \
                and "eyko114" not in r["file"]:
            groups[(r["dev"], r["method"])][cond].append(r)
    keys = [k for k in sorted(groups, key=lambda k: (list(DEVICES).index(k[0]) if k[0] in DEVICES else 9, k[1]))
            if len(groups[k]) > 1]
    fig, panels = plt.subplots(1, len(keys), figsize=(3.6 * len(keys), 4.4))
    panels = panels if len(keys) > 1 else [panels]
    for ax, (dev, method) in zip(panels, keys):
        label, colour, _ = style(dev)
        conds = list(groups[(dev, method)])
        for j, n in enumerate((20_000, 100_000)):
            vals = []
            for c in conds:
                v = [num(r["median_ms"]) for r in groups[(dev, method)][c] if int(r["n"]) == n]
                vals.append(statistics.median(v) if v else 0)
            xs = [k + (j - 0.5) * 0.4 for k in range(len(conds))]
            ax.bar(xs, vals, 0.38, color=colour, alpha=1.0 if n == 100_000 else 0.45, zorder=2,
                   label=f"{n // 1000}k rows")
            for x, y in zip(xs, vals):
                if y:
                    ax.annotate(f"{y:.0f}" if y >= 10 else f"{y:.1f}", (x, y), xytext=(0, 2), textcoords="offset points",
                                ha="center", fontsize=6.5, color=INK)
        frame(ax, xlabel="", ylabel="ms per search, median" if ax is panels[0] else "", logx=False)
        ax.set_xticks(range(len(conds)), conds, rotation=30, ha="right", fontsize=7)
        ax.set_title(f"{label}\n{method}", color=colour, fontsize=8.5, loc="left", fontweight="bold")
        ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
        ax.legend(frameon=False, fontsize=6.5, loc="upper right", ncol=2)
    save(fig, "6-heat-and-battery", "6 · Cool, hot and low battery: median search time at 20k and 100k rows",
         "Condition from the file name (CONDITIONS in the script). Each panel compares runs of one method on one phone; "
         "panels with a single condition are left out.")


# ---------------------------------------------------------------- graph 7
def fit(points):
    ns, ms = list(points), [v[0] for v in points.values()]
    mn, mm = statistics.mean(ns), statistics.mean(ms)
    b = sum((n - mn) * (m - mm) for n, m in zip(ns, ms)) / sum((n - mn) ** 2 for n in ns)
    return mm - b * mn, b


def graph_capacity(rows):
    """Days until one vector search passes each budget, by hours of video a day (the app's search as it is now)."""
    hours = [0.25, 0.5, 1, 2, 4]
    styles = {100: (0, (1, 2)), 200: "-", 500: (0, (5, 3))}
    runs = []
    for dev, pattern in CAPACITY_RUNS.items():
        sel = [r for r in rows if r["dev"] == dev and r["method"] == "offheap_mapped_native" and Path(r["file"]).match(pattern)]
        by = defaultdict(list)
        for r in sel:
            by[int(r["n"])].append(num(r["median_ms"]))
        if by:
            runs.append((dev, {n: (statistics.median(v), 0) for n, v in sorted(by.items())}, sel[0]["file"], False))
    for dev in [d for d in DEVICES if d != "laptop" and d not in CAPACITY_RUNS]:
        pts, name = series(rows, dev, "blob_memory_fast")  # stand-in: never timed the app's current search
        pts = {n: v for n, v in pts.items() if 20_000 <= n <= 100_000}
        if len(pts) >= 2:
            runs.append((dev, pts, name, True))
    runs.sort(key=lambda r: list(DEVICES).index(r[0]) if r[0] in DEVICES else 9)
    fig, panels = plt.subplots(1, len(runs), figsize=(5.4 * len(runs), 4.4), sharey=True)
    panels = panels if len(runs) > 1 else [panels]
    for ax, (dev, pts, file, standin) in zip(panels, runs):
        label, colour, marker = style(dev)
        a, b = fit(pts)
        for budget in BUDGETS_MS:
            n_at = (budget - a) / b
            where = "measured range" if n_at <= max(pts) else "extrapolated" if n_at <= 300_000 else "past the tests and the 300k trigger"
            ax.plot(hours, [n_at / (h * KEPT_PER_HOUR) for h in hours], color=colour, linestyle=styles[budget], linewidth=2,
                    marker=marker, markersize=4, label=f"{budget} ms (assumed): {n_at / 1000:,.0f}k rows, {where}")
            print(f"graph 7: {dev}{' (stand-in)' if standin else ''} {budget} ms -> {n_at:,.0f} rows; days at 1 h a day {n_at / KEPT_PER_HOUR:,.0f}")
        ax.axhline(365, color=GRID, linewidth=1.2)
        ax.annotate("1 year", (hours[0], 365), xytext=(2, -9), textcoords="offset points", fontsize=7, color=MUTED)
        ax.set_xscale("log")
        ax.set_yscale("log")
        frame(ax, xlabel="Hours of video recorded a day", ylabel="Days until a search passes the budget" if ax is panels[0] else "",
              logx=False)
        ax.set_xticks(hours, ["15 min", "30 min", "1 h", "2 h", "4 h"])
        ax.minorticks_off()
        how = "STAND-IN: the exact fast loop, not the app's search" if standin else condition_of(file)
        ax.set_title(f"{label}, {how}\n{b * 1000:.2f} ms more per 1,000 rows", color=colour, fontsize=8.5, loc="left")
        ax.legend(frameon=False, fontsize=6.5, loc="lower left")
    save(fig, "7-capacity", "7 · Days of recording before one vector search passes 100, 200 or 500 ms",
         "The app's search (MAPPED_NATIVE) measured at 20k-100k, a straight line through it, 13.4 kept frames a minute "
         "(Head 8). The Infinix never timed the app's search: its exact fast loop stands in (on the A32 the two are within 7 %). "
         "Budgets and hours a day are assumptions (EYKO-101).")


def main():
    OUT.mkdir(exist_ok=True)
    rows, storage = read_all()
    if not rows:
        sys.exit(f"no shared-format CSV under {DATA}")
    graph_time(rows)
    graph_memory(rows)
    graph_file_size(rows)
    graph_devices(rows)
    graph_storage(storage)
    graph_heat(rows)
    graph_capacity(rows)


if __name__ == "__main__":
    main()
