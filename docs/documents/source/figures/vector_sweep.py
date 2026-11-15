# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["matplotlib==3.9.2"]
# ///
"""Head 2 graphs from the phone vector tests with real vectors (EYKO-100; EYKO-95 adds the Infinix).

Reads docs/results/vectors/*-sweep-real.csv and *-memory.csv and redraws the same five PNGs next
to this file, so a new phone or a rerun replaces the old images. The random-vector sweep
(EYKO-90, *-sweep.csv) gave the same times and is kept as raw data only, not drawn.
No speed limit line is drawn: the 200 ms target has no source yet (EYKO-101). When one phone has several sweep files, the
newest file wins and the older ones are printed as superseded.

EYKO-97 adds four more (file size, the laptop against three phones, storage per hour, and the capacity model);
see docs/results/2026-11-15-vectors-graphs-and-capacity.md.

Run from the repo root:  uv run docs/documents/source/figures/vector_sweep.py   (or: task vectors-plots)
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
RESULTS = HERE.parents[2] / "results" / "vectors"
HEAP_LIMIT_MB = 268  # Java heap growth limit both phones reported (measured: device sheet in every run)

# Colour and marker follow the phone, never its rank (checked with the dataviz validator).
PHONES = {
    "samsung SM-A325F": ("Samsung A32", "#2a78d6", "o"),
    "Google Pixel 9 Pro XL": ("Pixel 9 Pro XL", "#eb6834", "s"),
}
SPARE = [("#1baf7a", "^"), ("#6250d6", "D"), ("#e87ba4", "v")]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def load(pattern="*-sweep.csv"):
    """{device: rows} from the newest file of each device matching pattern."""
    newest = {}
    for path in sorted(RESULTS.glob(pattern)):
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        if not rows:
            continue
        device = rows[0]["device"]
        if device.startswith("laptop"):  # EYKO-91's laptop sweeps share this folder; these figures are phones only
            continue
        key = (rows[0]["date"], path.name)
        if device in newest:
            old = newest[device]
            if key > old[0]:
                print(f"superseded: {old[1].name} (newer: {path.name})")
                newest[device] = (key, path, rows)
            else:
                print(f"superseded: {path.name} (newer: {old[1].name})")
        else:
            newest[device] = (key, path, rows)
    for device, (_, path, _) in newest.items():
        print(f"using: {path.name} for {device}")
    return {device: rows for device, (_, _, rows) in newest.items()}


def style(device, i):
    if device in PHONES:
        return PHONES[device]
    colour, marker = SPARE[i % len(SPARE)]
    return device, colour, marker


def by_size(rows, method, column):
    """{n: [values of column over the runs]} and the sizes that failed (with their note)."""
    values, failed = defaultdict(list), {}
    for r in rows:
        if r["method"] != method:
            continue
        n = int(r["n"])
        if r[column]:
            values[n].append(float(r[column]))
        elif r["note"].startswith("OutOfMemoryError"):
            failed[n] = r["note"]
    return dict(sorted(values.items())), failed


def axes(ax, ylabel):
    ax.set_xscale("log")
    ax.set_xlabel("Vectors in the table (512 numbers each)", color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.set_xticks([1_000, 5_000, 20_000, 50_000, 100_000, 300_000], ["1k", "5k", "20k", "50k", "100k", "300k"])
    ax.minorticks_off()


def line(ax, sizes, values, colour, marker, label):
    medians = [statistics.median(v) for v in values]
    low = [m - min(v) for m, v in zip(medians, values)]
    high = [max(v) - m for m, v in zip(medians, values)]
    ax.errorbar(sizes, medians, yerr=[low, high], color=colour, marker=marker, markersize=6,
                linewidth=2, capsize=3, markeredgecolor="white", markeredgewidth=1, label=label)
    return medians


def limit_line(ax, y, text):
    ax.axhline(y, color=MUTED, linestyle=(0, (4, 3)), linewidth=1)
    ax.annotate(text, (0.01, y), xycoords=("axes fraction", "data"), xytext=(0, 4),
                textcoords="offset points", color=MUTED, fontsize=8)


def ticks(ax, sizes):
    ax.set_xticks(sizes, [f"{n // 1000}k" for n in sizes])


def fig_memory(data):
    """Search from memory by table size, both phones on one chart (the app's loop until EYKO-102)."""
    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=200)
    for i, (device, rows) in enumerate(data.items()):
        label, colour, marker = style(device, i)
        values, _ = by_size(rows, "blob_memory_dot", "median_ms")
        medians = line(ax, list(values), list(values.values()), colour, marker, label)
        last = list(values)[-1]
        ax.annotate(f"{label} {medians[-1]:.0f} ms", (last, medians[-1]), xytext=(6, -3),
                    textcoords="offset points", color=INK, fontsize=8)
        sizes = list(values)
    axes(ax, "Search time per query, ms (median of 20)")
    ticks(ax, sizes)
    ax.set_xlim(700, 300_000)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    ax.set_title("Vector search from memory: time per query by table size (real vectors)", color=INK, fontsize=10, loc="left")
    save(fig, "head2-vector-memory-speed.png")


def fig_methods(data):
    """Kept in memory vs read from SQLite on every query, one panel per phone (real vectors: the
    read-from-SQLite method was timed at the small sizes only, because one query takes seconds)."""
    fig, panels = plt.subplots(1, len(data), figsize=(7.2, 3.6), dpi=200, sharey=True)
    panels = panels if len(data) > 1 else [panels]
    for i, (ax, (device, rows)) in enumerate(zip(panels, data.items())):
        label, colour, marker = style(device, i)
        mem, _ = by_size(rows, "blob_memory_dot", "median_ms")
        disk, _ = by_size(rows, "blob_disk_dot", "median_ms")
        shared = [n for n in disk if n in mem]
        a = line(ax, shared, [mem[n] for n in shared], colour, marker, "kept in memory")
        b = line(ax, shared, [disk[n] for n in shared], MUTED, marker, "read from SQLite every query")
        ax.annotate(f"{a[-1]:.0f} ms", (shared[-1], a[-1]), xytext=(6, -3), textcoords="offset points", fontsize=8, color=INK)
        ax.annotate(f"{b[-1]:.0f} ms", (shared[-1], b[-1]), xytext=(6, -3), textcoords="offset points", fontsize=8, color=INK)
        ax.set_yscale("log")
        axes(ax, "ms per query (median of 20), log scale" if i == 0 else "")
        ticks(ax, shared)
        ax.set_xlim(shared[0] * 0.6, shared[-1] * 2.5)
        ax.set_title(label, color=INK, fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.suptitle("Kept in memory vs read from SQLite on every query (real vectors)", color=INK, fontsize=10, x=0.01, ha="left")
    save(fig, "head2-vector-memory-vs-disk.png")


def fig_heap(data):
    """One table: the block its vectors need (n x 512 x 4 bytes) against the heap limit, with each
    phone's measured outcome (filled mark: the search ran). The line goes on to 300k as plain
    arithmetic; 300k was run only with random vectors (3 Nov), where it ran out of memory."""
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=200)
    sizes = sorted({int(r["n"]) for rows in data.values() for r in rows})
    line_sizes = sizes + [300_000]
    need = {n: n * 512 * 4 / 1e6 for n in line_sizes}
    ax.plot(line_sizes, [need[n] for n in line_sizes], color=GRID, linewidth=6, solid_capstyle="round", zorder=1)
    ax.annotate("memory one table needs (n × 512 × 4 bytes)", (sizes[-1], need[sizes[-1]]), xytext=(-8, 10),
                textcoords="offset points", ha="right", color=MUTED, fontsize=8)
    count = len(data)
    for i, (device, rows) in enumerate(data.items()):
        label, colour, marker = style(device, i)
        ran, _ = by_size(rows, "blob_memory_dot", "median_ms")
        shift = 1 + (i - (count - 1) / 2) * 0.06  # side by side, so both marks show at the same size
        ax.scatter([n * shift for n in ran], [need[n] for n in ran], color=colour, marker=marker, s=46,
                   edgecolors="white", linewidths=1, zorder=3, label=f"{label}: search ran")
    ax.annotate("300k would need one 614 MB block (computed);\nit ran out of memory in the 3 Nov run",
                (300_000, need[300_000]), xytext=(-12, -4), textcoords="offset points", ha="right", va="top",
                color=INK, fontsize=8)
    limit_line(ax, HEAP_LIMIT_MB, f"Java heap limit Android gives the app: {HEAP_LIMIT_MB} MB")
    axes(ax, "MB")
    ticks(ax, line_sizes)
    ax.set_ylim(0, 680)
    ax.set_xlim(700, 450_000)
    ax.legend(frameon=False, loc="upper left", fontsize=7.5)
    ax.set_title("One table in memory: what its vectors need vs the app's heap limit", color=INK, fontsize=10, loc="left")
    save(fig, "head2-vector-heap.png")


def fig_fast_loop(data):
    """EYKO-100: the app's loop vs the faster loop, real vectors, one panel per phone."""
    fig, panels = plt.subplots(1, len(data), figsize=(7.2, 3.6), dpi=200, sharey=True)
    panels = panels if len(data) > 1 else [panels]
    for i, (ax, (device, rows)) in enumerate(zip(panels, data.items())):
        label, colour, marker = style(device, i)
        app, _ = by_size(rows, "blob_memory_dot", "median_ms")
        fast, _ = by_size(rows, "blob_memory_fast", "median_ms")
        a = line(ax, list(app), list(app.values()), MUTED, marker, "the app's loop until EYKO-102")
        b = line(ax, list(fast), list(fast.values()), colour, marker, "faster loop (same top 20; in the app since EYKO-102)")
        last = list(app)[-1]
        ax.annotate(f"{a[-1]:.0f} ms", (last, a[-1]), xytext=(6, -3), textcoords="offset points", fontsize=8, color=INK)
        ax.annotate(f"{b[-1]:.0f} ms", (last, b[-1]), xytext=(6, -3), textcoords="offset points", fontsize=8, color=INK)
        axes(ax, "ms per query (median of 20)" if i == 0 else "")
        ax.set_xticks(list(app), [f"{n // 1000}k" for n in app])
        ax.set_xlim(700, 200_000)
        ax.set_ylim(0, 600)
        ax.set_title(label, color=INK, fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.suptitle("Search from memory with real vectors: the app's loop vs a faster loop", color=INK, fontsize=10, x=0.01, ha="left")
    save(fig, "head2-vector-fast-loop.png")


def fig_all_tables(data):
    """EYKO-100: three tables (image 512, text 384, audio-sized 512) loaded together, n rows each."""
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=200)
    sizes = sorted({int(r["n"]) for rows in data.values() for r in rows})
    need = {n: n * (512 + 384 + 512) * 4 / 1e6 for n in sizes}
    ax.plot(sizes, [need[n] for n in sizes], color=GRID, linewidth=6, solid_capstyle="round", zorder=1)
    ax.annotate("memory all three tables need", (sizes[1], need[sizes[1]]), xytext=(-8, 8),
                textcoords="offset points", ha="right", color=MUTED, fontsize=8)
    count = len(data)
    for i, (device, rows) in enumerate(data.items()):
        label, colour, marker = style(device, i)
        shift = 1 + (i - (count - 1) / 2) * 0.06
        for r in rows:
            n = int(r["n"])
            note = dict(part.strip().split("=", 1) for part in r["note"].split(";") if "=" in part)
            held, loaded = float(note["vectors_held_mb"]), note["tables_loaded"]
            ok = loaded.startswith("3")
            ax.scatter([n * shift], [held], color=colour, marker=marker if ok else "x", s=46 if ok else 60,
                       linewidths=1 if ok else 2, edgecolors="white" if ok else None, zorder=3,
                       label=f"{label}: all 3 loaded" if ok else f"{label}: out of memory")
            if not ok and i == count - 1:
                ax.annotate(f"only {loaded} tables fit", (n, held), xytext=(10, -4), textcoords="offset points",
                            color=INK, fontsize=8)
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    limit_line(ax, HEAP_LIMIT_MB, f"Java heap limit Android gives the app: {HEAP_LIMIT_MB} MB")
    axes(ax, "MB of vectors in memory")
    ax.set_xlabel("Rows in each table (image 512 + text 384 + audio 512 numbers per row)", color=MUTED)
    ax.set_xticks(sizes, [f"{n // 1000}k" for n in sizes])
    ax.set_xlim(3_500, 150_000)
    ax.set_ylim(0, 600)
    ax.legend(unique.values(), unique.keys(), frameon=False, loc="upper left", fontsize=7.5)
    ax.set_title("All three vector tables in memory: where the app runs out", color=INK, fontsize=10, loc="left")
    save(fig, "head2-vector-all-tables.png")


# EYKO-109: the five ways of holding the vectors, Infinix X670 only (colour follows the way, not its rank).
VARIANTS = {
    "heap_f32": ("Java array (as before)", "#0b0b0b", "o"),
    "offheap_f32": ("float32, direct buffers", "#2a78d6", "s"),
    "offheap_f16": ("float16, direct buffers", "#eb6834", "^"),
    "offheap_i8_rescore": ("int8 + exact re-check", "#6250d6", "D"),
    "offheap_mapped_f32": ("float32, memory-mapped file", "#1baf7a", "v"),
}


def variant_rows(kind):
    """Rows of the EYKO-109 Infinix CSVs (offheap/*eyko109-<kind>-*.csv); a later file replaces an earlier one for the same (method, n)."""
    rows = {}
    for path in sorted((RESULTS / "offheap").glob(f"*eyko109-{kind}-*.csv")):
        for r in csv.DictReader(path.open(encoding="utf-8")):
            rows.setdefault((r["method"].removeprefix("memory_"), int(r["n"])), []).append((path.name, r))
    return {k: v[-1][1] if kind == "memory" else [x[1] for x in v if x[0] == v[-1][0]] for k, v in rows.items()}


def fig_variants():
    """EYKO-109: Java memory after loading three tables, and search time, for each way of holding the vectors."""
    memory, speed = variant_rows("memory"), variant_rows("speed")
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.2, 3.9), dpi=200)
    for method, (label, colour, marker) in VARIANTS.items():
        pts = sorted((n, r) for (m, n), r in memory.items() if m == method)
        xs, ys, bad = [], [], []
        for n, r in pts:
            note = dict(part.strip().split("=", 1) for part in r["note"].split(";") if "=" in part)
            (xs if note["tables_loaded"].startswith("3") else bad).append((n, float(note["java_after_mb"])))
        shift = 1 + (list(VARIANTS).index(method) - 2) * 0.04
        left.plot([n * shift for n, _ in xs], [v for _, v in xs], color=colour, marker=marker, markersize=6, linewidth=1.8,
                  markeredgecolor="white", markeredgewidth=1, label=label)
        left.scatter([n * shift for n, _ in bad], [v for _, v in bad], color=colour, marker="x", s=55, linewidths=2, zorder=3)
        sp = sorted((n, [float(r["median_ms"]) for r in rs if r["median_ms"]]) for (m, n), rs in speed.items() if m == method)
        sp = [(n, statistics.median(v)) for n, v in sp if v]
        right.plot([n for n, _ in sp], [v for _, v in sp], color=colour, marker=marker, markersize=6, linewidth=1.8,
                   markeredgecolor="white", markeredgewidth=1, label=label)
    limit_line(left, HEAP_LIMIT_MB, f"Java heap limit: {HEAP_LIMIT_MB} MB")
    axes(left, "Java memory after loading the three tables (MB)")
    axes(right, "Search time, all rows scored (ms, median)")
    right.set_yscale("log")
    left.set_xlabel("Rows in each of the three tables   (x = ran out of memory on the next table)", color=MUTED)
    right.set_xlabel("Rows in the image table (512 numbers each)", color=MUTED)
    for ax in (left, right):
        ax.set_xticks([5_000, 20_000, 50_000, 100_000, 200_000, 300_000], ["5k", "20k", "50k", "100k", "200k", "300k"])
        ax.set_xlim(3_500, 400_000)
    right.set_xlim(3_500, 150_000)
    left.legend(frameon=False, loc="lower right", bbox_to_anchor=(1.0, 0.10), fontsize=7)
    left.set_title("Memory: where each way runs out (Infinix X670)", color=INK, fontsize=10, loc="left")
    right.set_title("Speed: the same ways, one phone", color=INK, fontsize=10, loc="left")
    save(fig, "head2-vector-variants.png")


# EYKO-111: the app's setup against the old way, on battery. One file per panel (the clean run of that condition).
CONDITIONS = [
    ("Samsung A32, hot (after 10 min of video processing)", "a32-*-eyko111-hot2-*.csv"),
    ("Pixel 9 Pro XL, low battery (26 %, power saver off)", "pixel9proxl-*-eyko111-lowbat-nosaver-*.csv"),
]
SETUPS = [("heap_f32", "Java array (the old way)", "#0b0b0b"),
          ("offheap_mapped_native", "Mapped file + NEON (the app now)", "#1baf7a")]


def fig_conditions():
    """EYKO-111: median search time of 5 runs (bar) and their range (whisker), each phone on its own scale."""
    fig, panels = plt.subplots(1, len(CONDITIONS), figsize=(10.2, 3.6), dpi=200)
    width = 0.38
    for ax, (title, pattern) in zip(panels, CONDITIONS):
        (path,) = sorted((RESULTS / "offheap").glob(pattern))
        runs = defaultdict(list)
        for r in csv.DictReader(path.open(encoding="utf-8")):
            runs[(r["method"], int(r["n"]))].append(float(r["median_ms"]))
        sizes = sorted({n for _, n in runs})
        for i, (method, label, colour) in enumerate(SETUPS):
            xs = [k + (i - 0.5) * (width + 0.02) for k in range(len(sizes))]
            vals = [runs[(method, n)] for n in sizes]
            med = [statistics.median(v) for v in vals]
            err = [[m - min(v) for m, v in zip(med, vals)], [max(v) - m for m, v in zip(med, vals)]]
            ax.bar(xs, med, width, color=colour, label=label, yerr=err, ecolor=MUTED, capsize=2, zorder=2)
        for k, n in enumerate(sizes):
            old = statistics.median(runs[("heap_f32", n)])
            new = statistics.median(runs[("offheap_mapped_native", n)])
            top = max(runs[("offheap_mapped_native", n)])  # above the whisker, not on it
            ax.annotate(f"{new / old:.2f}×", (k + 0.2, top), xytext=(0, 4), textcoords="offset points",
                        ha="center", color=INK, fontsize=8)
        ax.set_xticks(range(len(sizes)), [f"{n // 1000}k" for n in sizes])
        ax.set_xlabel("Vectors in the table (512 numbers each)", color=MUTED)
        ax.set_ylabel("Search time, median of 5 runs (ms)", color=MUTED)
        ax.grid(True, axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(MUTED)
        ax.tick_params(colors=MUTED)
        ax.set_title(title, color=INK, fontsize=10, loc="left")
    panels[0].legend(frameon=False, loc="upper left", fontsize=8)
    save(fig, "head2-vector-conditions.png")


# ---- EYKO-97: the graphs Head 2 did not have yet ----
DEVICES = {  # colour follows the device in every EYKO-97 graph (A32 and Pixel as in Rafique's figures above)
    "A32": ("Samsung A32", "#2a78d6", "o"),
    "Pixel": ("Pixel 9 Pro XL", "#eb6834", "s"),
    "Infinix": ("Infinix X670", "#1baf7a", "^"),
    "laptop": ("Laptop i5-10310U", "#6250d6", "D"),
}
KEPT_PER_HOUR = 13.4 * 60  # kept frames per hour of video: Ego4D Pixel run, 372 kept in 27.8 min (Head 8); one image vector each
BUDGETS_MS = [100, 200, 500]  # assumptions, not sourced limits (the 200 ms target was dropped on 8 Nov; EYKO-101)


def medians(path, method, column="median_ms"):
    """{n: median over runs of column} for one method in one CSV."""
    runs = defaultdict(list)
    for r in csv.DictReader(path.open(encoding="utf-8")):
        if r["method"] == method and r[column]:
            runs[int(r["n"])].append(float(r[column]))
    return {n: statistics.median(v) for n, v in sorted(runs.items())}


def one(pattern):
    (path,) = sorted(RESULTS.glob(pattern))
    return path


def plain(ax, ylabel, xlabel="Vectors in the table (512 numbers each)"):
    axes(ax, ylabel)
    ax.set_xlabel(xlabel, color=MUTED)


def bytes_per_row(page_size, dims=512, rows=5_000):
    """Measured here, now: bytes one vector row takes in a plain BLOB table (the app's layout) at a page size."""
    import os
    import sqlite3
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "v.db")
        con = sqlite3.connect(path)
        con.execute(f"PRAGMA page_size={page_size}")
        con.execute("CREATE TABLE image_vec (frame_id INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
        con.executemany("INSERT INTO image_vec VALUES (?, ?)", ((i, bytes(4 * dims)) for i in range(rows)))
        con.commit()
        con.close()
        return os.path.getsize(path) / rows


def fig_file_size():
    """Card graph 3: how big one image table is on the phone's storage, by way of storing it."""
    fig, ax = plt.subplots(figsize=(7.6, 4.2), dpi=200)
    blob = medians(one("a32-2026-11-04-sweep-real.csv"), "blob_memory_fast", "file_mb")
    vec0 = medians(one("routes/a32-eyko105-route-r1-SM_A325F-20261108-1349.csv"), "sqlite_vec_bundled", "file_mb")
    int8 = medians(one("laptop-2026-11-07-sweep-real.csv"), "sqlite_vec_int8", "file_mb")
    sizes = [1_000, 5_000, 20_000, 50_000, 100_000, 300_000]
    per16k = bytes_per_row(16_384)
    series = [
        ("BLOB table, 4 KB pages (the app today; A32, measured)", "#0b0b0b", "o", "-", blob),
        ("sqlite-vec float32 (A32 route R1, measured)", "#eda100", "s", "-", vec0),
        ("mapped .vec file, the app's search copy (n × 2,048 B)", "#1baf7a", None, (0, (4, 3)),
         {n: n * 2048 / 1e6 for n in sizes}),
        (f"BLOB table, 16 KB pages ({per16k:,.0f} B a row, measured on the laptop)", "#2a78d6", None, (0, (1, 2)),
         {n: n * per16k / 1e6 for n in sizes}),
        ("sqlite-vec int8 (laptop, measured; not exact)", "#e87ba4", "^", "-", int8),
    ]
    for label, colour, marker, ls, pts in series:
        ax.plot(list(pts), list(pts.values()), color=colour, marker=marker, linestyle=ls, linewidth=2, markersize=5,
                markeredgecolor="white", markeredgewidth=1, label=label)
    ax.set_yscale("log")
    plain(ax, "MB on storage, one image table (log scale)")
    ax.set_xlim(700, 400_000)
    ax.annotate(f"{blob[100_000]:.0f} MB", (100_000, blob[100_000]), xytext=(6, 4), textcoords="offset points", fontsize=8, color=INK)
    ax.annotate(f"{vec0[100_000]:.0f} MB", (100_000, vec0[100_000]), xytext=(6, -10), textcoords="offset points", fontsize=8, color=INK)
    ax.legend(frameon=False, loc="upper left", fontsize=7)
    ax.set_title("File size: a 512-number vector takes a whole 4 KB page in the app's BLOB table", color=INK, fontsize=10, loc="left")
    save(fig, "head2-vector-file-size.png")
    return per16k


def fig_devices():
    """Card graph 4: the same exact search on the laptop and on all three phones (bars, log scale)."""
    runs = [
        ("laptop", one("laptop-2026-11-07-sweep-real.csv"), "blob_memory_numpy_1t", "numpy, 1 thread, 7 Nov"),
        ("Pixel", one("pixel9proxl-2026-11-04-sweep-real.csv"), "blob_memory_fast", "fast loop, cable, 4 Nov"),
        ("Infinix", one("infinix-2026-11-07-cool.csv"), "blob_memory_fast", "fast loop, cool run, 7 Nov; random vectors, same time as real, B3"),
        ("A32", one("a32-2026-11-04-sweep-real.csv"), "blob_memory_fast", "fast loop, cable, 4 Nov"),
    ]
    sizes = [5_000, 20_000, 50_000, 100_000]
    fig, ax = plt.subplots(figsize=(7.6, 4.0), dpi=200)
    width = 0.2
    for i, (key, path, method, how) in enumerate(runs):
        label, colour, _ = DEVICES[key]
        vals = medians(path, method)
        xs = [k + (i - 1.5) * width for k in range(len(sizes))]
        ys = [vals[n] for n in sizes]
        ax.bar(xs, ys, width * 0.92, color=colour, label=f"{label} ({how})", zorder=2)
        for x, y in zip(xs, ys):
            ax.annotate(f"{y:.0f}" if y >= 10 else f"{y:.1f}", (x, y), xytext=(0, 2), textcoords="offset points",
                        ha="center", fontsize=6.5, color=INK)
    ax.set_yscale("log")
    ax.set_xticks(range(len(sizes)), [f"{n // 1000}k" for n in sizes])
    ax.set_xlabel("Vectors in the table (512 numbers each)", color=MUTED)
    ax.set_ylabel("ms per search, median (log scale)", color=MUTED)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.legend(frameon=False, loc="upper left", fontsize=7)
    ax.set_title("The same exact search on the laptop and three phones", color=INK, fontsize=10, loc="left")
    save(fig, "head2-vector-devices.png")


def fig_storage():
    """Card graph 5: what one hour of camera video costs on the phone, before and after EYKO-126 (no copy).
    Numbers from the two result files named in the figure; the copy and audio are measured or exact, the rest calculated."""
    bars = [  # (label, [(part, MB)])
        ("Before EYKO-126\n(the app copied the video)", [("copy of the video", 9010), ("16 kHz audio", 115), ("frames, rows, vectors", 30)]),
        ("Now, since 13 Nov\n(read in place, no copy)", [("copy of the video", 0), ("16 kHz audio", 115), ("frames, rows, vectors", 11)]),
    ]
    colours = {"copy of the video": "#9a9893", "16 kHz audio": "#2a78d6", "frames, rows, vectors": "#eb6834"}
    fig, ax = plt.subplots(figsize=(7.6, 3.0), dpi=200)
    for y, (label, parts) in enumerate(bars):
        left = 0
        for part, mb in parts:
            ax.barh(y, mb, left=left, color=colours[part], height=0.55, label=part if y == 0 else None, zorder=2)
            left += mb
        ax.annotate(f"{left / 1000:.1f} GB" if left >= 1000 else f"{left:.0f} MB", (left, y), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9, color=INK)
    ax.set_yticks([0, 1], [b[0] for b in bars])
    ax.invert_yaxis()
    ax.set_xlabel("MB of app storage per hour of 1080p camera video (20 Mbps)", color=MUTED)
    ax.set_xlim(0, 10_400)
    ax.grid(True, axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.legend(frameon=False, loc="lower right", fontsize=7.5)
    ax.set_title("Storage per hour of camera video, before and after EYKO-126", color=INK, fontsize=10, loc="left")
    save(fig, "head2-storage-per-hour.png")


def fit(points):
    """Least-squares line ms = a + b * n through {n: ms}."""
    ns, ms = list(points), list(points.values())
    mean_n, mean_m = statistics.mean(ns), statistics.mean(ms)
    b = sum((n - mean_n) * (m - mean_m) for n, m in zip(ns, ms)) / sum((n - mean_n) ** 2 for n in ns)
    return mean_m - b * mean_n, b


def fig_capacity():
    """Card graph 7: days until one search takes longer than a budget, by hours of video a day.
    Search time is the app's (MAPPED_NATIVE) measured at 20k, 50k and 100k rows; a straight line through them gives the
    rows at each budget. Rows per day = hours x 13.4 kept frames a minute x 60."""
    phones = [
        ("A32", "Samsung A32, hot, on battery (EYKO-111)", one("offheap/a32-*-eyko111-hot2-*.csv")),
        ("Pixel", "Pixel 9 Pro XL, 26 % battery (EYKO-111)", one("offheap/pixel9proxl-*-eyko111-lowbat-nosaver-*.csv")),
    ]
    hours = [0.25, 0.5, 1, 2, 4]
    styles = {100: (0, (1, 2)), 200: "-", 500: (0, (5, 3))}
    fig, panels = plt.subplots(1, 2, figsize=(10.2, 4.0), dpi=200, sharey=True)
    table = []
    for ax, (key, title, path) in zip(panels, phones):
        _, colour, marker = DEVICES[key]
        a, b = fit(medians(path, "offheap_mapped_native"))
        for budget in BUDGETS_MS:
            rows = (budget - a) / b
            days = [rows / (h * KEPT_PER_HOUR) for h in hours]
            where = "measured range" if rows <= 100_000 else "extrapolated" if rows <= 300_000 else "far past the tests and ADR 0001's 300k"
            ax.plot(hours, days, color=colour, linestyle=styles[budget], linewidth=2, marker=marker, markersize=4,
                    markeredgecolor="white", markeredgewidth=0.8, label=f"{budget} ms: {rows / 1000:,.0f}k rows ({where})")
            table.append((key, budget, rows, [rows / (h * KEPT_PER_HOUR) for h in (0.5, 1, 2)]))
        ax.axhline(365, color=GRID, linewidth=1.2, zorder=1)
        ax.annotate("1 year", (hours[0], 365), xytext=(2, -9), textcoords="offset points", fontsize=7, color=MUTED)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks(hours, ["15 min", "30 min", "1 h", "2 h", "4 h"])
        ax.minorticks_off()
        ax.set_xlabel("Hours of video recorded a day", color=MUTED)
        ax.grid(True, which="major", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(MUTED)
        ax.tick_params(colors=MUTED)
        ax.set_title(f"{title}\n{b * 1000:.2f} ms more per 1,000 rows", color=INK, fontsize=9, loc="left")
        ax.legend(frameon=False, loc="lower left", fontsize=7)
    panels[0].set_ylabel("Days until a search passes the budget", color=MUTED)
    fig.suptitle("Capacity: days of recording before one vector search passes 100, 200 or 500 ms (assumed budgets, EYKO-101)",
                 color=INK, fontsize=10, x=0.01, y=1.0, ha="left")
    save(fig, "head2-capacity.png")
    for key, budget, rows, days in table:
        print(f"capacity {key} {budget} ms: {rows:,.0f} rows; days at 0.5/1/2 h a day: " + " / ".join(f"{d:,.0f}" for d in days))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(HERE / name, facecolor="#fcfcfb")
    plt.close(fig)
    print(f"wrote {name}")


if __name__ == "__main__":
    plt.rcParams["font.family"] = "Calibri"
    real = load("*-sweep-real.csv")
    fig_memory(real)
    fig_methods(real)
    fig_heap(real)
    fig_fast_loop(real)
    fig_all_tables(load("*-memory.csv"))
    fig_variants()
    fig_conditions()
    print(f"BLOB row at 16 KB pages: {fig_file_size():,.0f} B; at 4 KB: {bytes_per_row(4096):,.0f} B; at 8 KB: {bytes_per_row(8192):,.0f} B")
    fig_devices()
    fig_storage()
    fig_capacity()
