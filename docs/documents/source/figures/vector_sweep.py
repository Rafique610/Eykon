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

Run from the repo root:  uv run docs/documents/source/figures/vector_sweep.py
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
