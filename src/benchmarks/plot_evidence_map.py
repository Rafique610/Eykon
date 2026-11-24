"""Graphs for docs/head2-head3-evidence-map.md that no earlier card drew. Run: task evidence-map-plots

Every number is measured, and comes from the result file named next to it (copied here because those files hold it as a
table, not a CSV). Graph 6 is computed from the Pixel's own crop vectors and the person-checked groups (EYKO-15, EYKO-72).
Writes docs/results/evidence-map/<name>.png and .svg.
"""

import csv
import json
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "docs/results"
OUT = RESULTS / "evidence-map"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
PIXEL, INFINIX, A32 = "#eb6834", "#1baf7a", "#2a78d6"  # the device colours of plot_vector_storage.py
BEFORE = "#a9a8a3"  # "before" is always grey, "after" wears the phone's colour
GOOD, BAD = "#008300", "#c8102e"


def frame(ax, xlabel, ylabel):
    ax.set_xlabel(xlabel, color=MUTED, fontsize=8)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=8)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
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
    top = 1 - (0.42 + 0.17 * len(lines)) / h
    fig.text(0.01, 1 - 0.1 / h, title, ha="left", va="top", fontsize=11, color=INK, fontweight="bold")
    fig.text(0.01, 1 - 0.36 / h, "\n".join(lines), ha="left", va="top", fontsize=8, color=MUTED, linespacing=1.4)
    fig.tight_layout(rect=(0, 0, 1, top))
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=170, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote evidence-map/{name}.png and .svg")


def label_bars(ax, bars, fmt):
    for b in bars:
        ax.annotate(fmt(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()), xytext=(0, 2),
                    textcoords="offset points", ha="center", fontsize=7, color=INK)


def mapped_adoption():
    # 2026-11-08-adopt-mapped.md, A32 on the cable, median of 5 runs, ms per search
    rows = ["20k", "50k", "100k"]
    before = [115.2, 283.7, 565.2]  # EYKO-114 HEAP_F32 with COUNT(*) on every search (the app before)
    after = [21.3, 52.1, 102.5]  # MAPPED_NATIVE, MAX(id) check (the app now)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = np.arange(len(rows))
    label_bars(ax, ax.bar(x - 0.2, before, 0.38, color=BEFORE, label="before: vectors in Java memory, COUNT(*) per search"), lambda v: f"{v:.0f}")
    bars = ax.bar(x + 0.2, after, 0.38, color=A32, label="after: memory-mapped file + NEON, MAX(id) check")
    label_bars(ax, bars, lambda v: f"{v:.0f}")
    for i in range(len(rows)):
        ax.annotate(f"{before[i] / after[i]:.1f}× faster", (x[i] + 0.2, after[i]), xytext=(0, 14), textcoords="offset points",
                    ha="center", fontsize=7.5, color=MUTED)
    ax.set_xticks(x, rows)
    frame(ax, "Vectors in the table (512 numbers each)", "ms per search (median of 5)")
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    save(fig, "1-mapped-adoption-a32", "Vector search before and after the memory-mapped NEON file (A32)",
         "Samsung A32, cable in, median of 5 runs, same answers bit for bit. Source: docs/results/2026-11-08-adopt-mapped.md (EYKO-115).")


def background_kill():
    # 2026-11-09-background-kill-mapped-native.md, Infinix X670, MAPPED_NATIVE, three tables, 300 s hold in the background
    runs = [(20_000, 300, True), (30_000, 300, True), (40_000, 267, False), (50_000, 287, False), (70_000, 278, False),
            (100_000, 187, False), (100_000, 211, False), (100_000, 218, False)]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for alive, colour, name in ((True, GOOD, "survived the 300 s hold"), (False, BAD, "killed by Android")):
        pts = [(n / 1000, s) for n, s, a in runs if a == alive]
        ax.scatter(*zip(*pts), s=46, color=colour, marker="o" if alive else "X", label=name, zorder=3, edgecolor=SURFACE, linewidth=1.5)
    ax.axhline(300, color=MUTED, linewidth=0.8, linestyle=(0, (4, 3)))
    ax.annotate("end of the hold (300 s)", (100, 300), xytext=(0, 3), textcoords="offset points", ha="right", fontsize=7, color=MUTED)
    ax.axvspan(30, 40, color=GRID, zorder=0)
    ax.annotate("the line is between\n30k and 40k rows", (35, 200), ha="center", fontsize=7.5, color=INK)
    ax.set_xticks([20, 30, 40, 50, 70, 100], ["20k", "30k", "40k", "50k", "70k", "100k"])
    ax.set_ylim(150, 320)
    frame(ax, "Rows in each of the 3 vector tables", "seconds alive in the background")
    ax.legend(fontsize=7.5, frameon=False, loc="lower left")
    save(fig, "2-background-kill-infinix", "With big vector tables the app is killed in the background (Infinix)",
         "Infinix X670, MAPPED_NATIVE, 3 tables held 300 s in the background, one dot per run (100k: 3 runs). Open risk: the planned "
         "100k does not survive. Source: docs/results/2026-11-09-background-kill-mapped-native.md (EYKO-116 part 1).")


def storage_per_hour():
    # 2026-11-13-read-from-gallery.md: copy every video ≈ 9.2 GB per hour of camera video (EYKO-116, calculated);
    # read in place ≈ 126 MB per hour (Pixel, measured)
    fig, ax = plt.subplots(figsize=(6, 3.4))
    bars = ax.bar(["before: copy every video\n(calculated, camera video)", "after: read from the gallery\n(measured, Pixel)"],
                  [9200, 126], 0.5, color=[BEFORE, PIXEL])
    label_bars(ax, bars, lambda v: f"{v:,.0f} MB")
    frame(ax, "", "app storage per hour of video (MB)")
    save(fig, "3-storage-per-hour", "App storage for one hour of video: about 70× less",
         "Before EYKO-126 every picked video was copied into the app; now the gallery file is read in place and only frames, "
         "audio and database rows are kept. Source: docs/results/2026-11-13-read-from-gallery.md.")


def minutes_in_500mb():
    # research/2026-11-16-head3-background-and-limits.md Part 2, and the A32 row from 2026-11-18-pr23-pixel-a32-checks.md
    rows = [("Pixel 9 Pro XL, 1080p HEVC (our clip)", 3.5, PIXEL), ("Samsung A32, 1080p (85 of our camera files)", 3.9, A32),
            ("Pixel 4, 1080p30 (web)", 4.0, BEFORE), ("Pixel 4, 4K30 (web)", 1.5, BEFORE), ("Pixel 6, 4K30 H.264 (web)", 1.5, BEFORE)]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    y = np.arange(len(rows))[::-1]
    bars = ax.barh(y, [r[1] for r in rows], 0.6, color=[r[2] for r in rows])
    for b, r in zip(bars, rows):
        ax.annotate(f"{r[1]} min", (b.get_width(), b.get_y() + b.get_height() / 2), xytext=(3, 0), textcoords="offset points",
                    va="center", fontsize=7.5, color=INK)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.set_xlim(0, 5)
    frame(ax, "minutes of video that fit in 500 MB", "")
    ax.grid(True, axis="x", color=GRID, linewidth=0.8)
    ax.grid(False, axis="y")
    save(fig, "4-minutes-in-500mb", "The old 500 MB limit held only 1.5 to 4 minutes of phone video",
         "Colour: measured on our phones; grey: from web sources. So the limit was removed (EYKO-126, PR #23). Sources: "
         "docs/research/2026-11-16-head3-background-and-limits.md, docs/results/2026-11-18-pr23-pixel-a32-checks.md.")


def split_speed():
    # 2026-11-17-split-frames-faster.md, kit clip 1 (74.5 s), whole split stage, range over the runs
    rows = [("Pixel 9 Pro XL\nbefore", 28.8, 32.2, BEFORE), ("Pixel 9 Pro XL\nafter d93c56b", 7.9, 10.4, PIXEL),
            ("Samsung A32\nafter", 24.0, 26.4, A32)]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    mids = [(lo + hi) / 2 for _, lo, hi, _ in rows]
    x = np.arange(len(rows))
    ax.bar(x, mids, 0.5, color=[r[3] for r in rows], yerr=[[m - r[1] for m, r in zip(mids, rows)], [r[2] - m for m, r in zip(mids, rows)]],
           ecolor=INK, capsize=4)
    for i, (_, lo, hi, _) in enumerate(rows):
        ax.annotate(f"{lo}–{hi} s", (x[i], hi), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=7.5, color=INK)
    ax.set_xticks(x, [r[0] for r in rows])
    ax.set_ylim(0, 38)
    frame(ax, "", "seconds for the split stage")
    save(fig, "5-split-faster", "Frame split about 3× faster on the Pixel, same JPEGs",
         "Kit clip 1 (74.5 s); bar = middle of the runs, whisker = their range. JPEGs are made a row at a time instead of a pixel at a time; every JPEG has the same hash before and "
         "after. No A32 run before the change. Source: docs/results/2026-11-17-split-frames-faster.md.")


def threshold():
    # the same pairs as src/benchmarks/crop_pairs.py: same name, different frames; groups as checked by a person (EYKO-72)
    crops = {c["crop"]: c for c in json.load(open(RESULTS / "latest/pixel9proxl-object-crops-2026-10-13.json", encoding="utf-8"))["crops"]}
    objects = {r["crop"]: r["object"] for r in csv.DictReader(open(RESULTS / "latest/crop-identity-2026-10-13-reviewed.csv", encoding="utf-8"))}
    same, different = [], []
    for a, b in combinations(sorted(objects), 2):
        ca, cb = crops[a], crops[b]
        if ca["label"] != cb["label"] or (ca["clip"], ca["frame_no"]) == (cb["clip"], cb["frame_no"]):
            continue
        (same if objects[a] == objects[b] else different).append(float(np.dot(ca["vector"], cb["vector"])))
    fig, ax = plt.subplots(figsize=(7, 3.6))
    bins = np.arange(0.45, 1.001, 0.025)
    ax.hist([different, same], bins, color=[BEFORE, PIXEL], edgecolor=SURFACE, linewidth=0.6,
            label=[f"different objects, same name ({len(different)} pairs)", f"same object ({len(same)} pairs)"])
    ax.axvline(0.87, color=INK, linewidth=1.2)
    missed, merged = sum(c < 0.87 for c in same), sum(c >= 0.87 for c in different)
    ax.annotate(f"0.87: {missed} of {len(same)} same pairs missed,\n{merged} of {len(different)} different pairs merged",
                (0.87, ax.get_ylim()[1] * 0.75), xytext=(6, 0), textcoords="offset points", ha="left", fontsize=7.5, color=INK)
    frame(ax, "cosine of the two crops' MobileCLIP vectors", "pairs")
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    save(fig, "6-same-object-threshold", "When are two sightings the same object? The 0.87 line",
         "The Pixel's 90 object crops (EYKO-15), pairs with the same name from different frames, grouped by a person (EYKO-72). "
         "The groups overlap, so some calls are wrong at any line. Source: docs/results/2026-10-13-eyko-15-crop-threshold.md.")
    print(f"threshold: same {len(same)}, different {len(different)}, missed {missed}, merged {merged}")


def _medians(path, method_prefix, column):
    """n -> median of `column` over the rows whose method is exactly `method_prefix` (the CSVs of the vector cards)."""
    got = {}
    for r in csv.DictReader(open(RESULTS / "vectors" / path, encoding="utf-8")):
        if r["method"] == method_prefix and r[column]:
            got.setdefault(int(r["n"]), []).append(float(r[column]))
    return {n: float(np.median(v)) for n, v in sorted(got.items())}


def memory_against_routes():
    # Three tables (image 512, text 384, audio 512) of n rows each; pss = whole app memory, heap = Java memory (limit 268 MB).
    # Speed: one image table, median of 5 run medians. All A32 except R4's memory (measured on the Infinix only).
    ways = [  # name, colour, marker, memory csv, memory method, speed csv, speed method
        ("our mapped file + NEON (the app)", A32, "o", "offheap/a32-2026-11-08-eyko114-memory-SM_A325F-20261108-1838.csv",
         "memory_offheap_mapped_native", "offheap/a32-2026-11-08-eyko115-speed-SM_A325F-20261108-1939.csv", "offheap_mapped_native"),
        ("R1 sqlite-vec, Google's bundled SQLite", "#e87ba4", "s", "routes/a32-eyko105-route-r1-memory-SM_A325F-20261108-1352.csv",
         "memory_all_tables_vec0", "routes/a32-eyko105-route-r1-SM_A325F-20261108-1349.csv", "sqlite_vec_bundled"),
        ("R2 sqlite-vec, requery (1 KB pages)", "#eda100", "D", "routes/a32-eyko106-route-r2-memory-SM_A325F-20261108-1533.csv",
         "memory_all_tables_vec0_requery", "routes/a32-eyko106-route-r2-SM_A325F-20261108-1528.csv", "sqlite_vec_requery"),
        ("R4 sqlite-vec, our own SQLite (memory: Infinix)", INFINIX, "^",
         "route-r4/infinix-2026-11-08-eyko108-r4-memory-neon-Infinix_X670-20261108-0204.csv", "memory_sqlite_vec_static",
         "routes/a32-eyko108-r4-neon-SM_A325F-20261108-1445.csv", "sqlite_vec_static"),
        ("old way: vectors in Java arrays", BEFORE, "v", "a32-2026-11-04-memory.csv", "memory_all_tables",
         "offheap/a32-2026-11-08-eyko115-speed-SM_A325F-20261108-1939.csv", "heap_f32"),
    ]
    sizes = [20_000, 50_000, 100_000]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    for name, colour, marker, mem_csv, mem_method, speed_csv, speed_method in ways:
        pss, heap = _medians(mem_csv, mem_method, "pss_mb"), _medians(mem_csv, mem_method, "heap_mb")
        speed = _medians(speed_csv, speed_method, "median_ms")
        for ax, values in ((axes[0], pss), (axes[1], heap), (axes[2], speed)):
            xs = [n for n in sizes if n in values]
            ax.plot([n / 1000 for n in xs], [values[n] for n in xs], color=colour, marker=marker, linewidth=2, markersize=6,
                    label=name, markeredgecolor=SURFACE)
    # The Java arrays could not hold all three tables (a32-2026-11-04-memory.csv: 2 of 3 at 50k, 1 of 3 at 100k)
    for ax in axes[:2]:
        for n, text, ha in ((50, "out of memory:\nonly 2 of 3 tables", "center"), (100, "out of memory:\nonly 1 of 3", "right")):
            y = (_medians("a32-2026-11-04-memory.csv", "memory_all_tables", "pss_mb" if ax is axes[0] else "heap_mb"))[n * 1000]
            ax.annotate(text, (n, y), xytext=(0, -26), textcoords="offset points", ha=ha, fontsize=6.5, color=BAD)
    axes[0].annotate("R1, R2, R4 all flat at 55–60 MB", (50, 60), xytext=(0, 6), textcoords="offset points", ha="center",
                     fontsize=7, color=INK)
    axes[1].annotate("our file and R1, R2, R4: 3–5 MB", (50, 5), xytext=(0, 6), textcoords="offset points", ha="center",
                     fontsize=7, color=INK)
    axes[1].axhline(268, color=BAD, linewidth=0.8, linestyle=(0, (4, 3)))
    axes[1].annotate("Java memory limit 268 MB", (20, 268), xytext=(0, 3), textcoords="offset points", fontsize=7, color=BAD)
    titles = [("All app memory (PSS, MB), 3 tables", "MB"), ("Java memory (MB), 3 tables", "MB"), ("Search time, image table (ms)", "ms")]
    for ax, (title, unit) in zip(axes, titles):
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.set_xticks([20, 50, 100], ["20k", "50k", "100k"])
        frame(ax, "rows in each table", unit)
    axes[0].legend(fontsize=7, frameon=False, loc="upper left")
    save(fig, "7-memory-and-speed-vs-sqlite-vec", "Memory and speed: our mapped file against sqlite-vec (R1, R2, R4) and Java arrays",
         "Samsung A32 unless noted, median of the runs. sqlite-vec keeps app memory flat (it reads from the database file) but searches "
         "2.3× (R1, R4) to 4.7× (R2, 1 KB pages; with 4 KB pages it runs at R1's speed) slower than ours at 100k, and R1 returns at most "
         "4,096 rows. Java arrays run out of Java memory at "
         "50k. Our file's pages count in PSS (Android can drop them, but large PSS is what got the app killed in the background, "
         "graph 2). Sources: docs/results/2026-11-08-route-r1-bundled.md, -route-r2-requery.md, -route-r4-static.md, "
         "-adopt-mapped.md; CSVs in docs/results/vectors/routes, route-r4, offheap.")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    memory_against_routes()
    mapped_adoption()
    background_kill()
    storage_per_hour()
    minutes_in_500mb()
    split_speed()
    threshold()
