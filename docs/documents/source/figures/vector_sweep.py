# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["matplotlib==3.9.2"]
# ///
"""Head 2 graphs from the phone vector sweep (EYKO-90 / EYKO-95).

Reads every docs/results/vectors/*-sweep.csv and redraws the same three PNGs next to this file,
so a new phone or a rerun replaces the old images. When one phone has several sweep files, the
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
LIMIT_MS = 200
HEAP_LIMIT_MB = 268  # Java heap growth limit both phones reported (EYKO-90 device sheet)

# Colour and marker follow the phone, never its rank (checked with the dataviz validator).
PHONES = {
    "samsung SM-A325F": ("Samsung A32", "#2a78d6", "o"),
    "Google Pixel 9 Pro XL": ("Pixel 9 Pro XL", "#eb6834", "s"),
}
SPARE = [("#1baf7a", "^"), ("#6250d6", "D"), ("#e87ba4", "v")]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def load():
    """{device: rows} from the newest sweep file of each device."""
    newest = {}
    for path in sorted(RESULTS.glob("*-sweep.csv")):
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


def fig_memory(data):
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=200)
    top = 0
    for i, (device, rows) in enumerate(data.items()):
        label, colour, marker = style(device, i)
        values, failed = by_size(rows, "blob_memory_dot", "median_ms")
        medians = line(ax, list(values), list(values.values()), colour, marker, label)
        top = max(top, max(max(v) for v in values.values()))
        last = list(values)[-1]
        ax.annotate(f"{label} {medians[-1]:.0f} ms", (last, medians[-1]), xytext=(6, -3),
                    textcoords="offset points", color=INK, fontsize=8)
        for n in failed:
            ax.scatter([n], [0], marker="x", s=60, color=colour, linewidths=2, clip_on=False, zorder=5)
    for n in sorted({n for rows in data.values() for n in by_size(rows, "blob_memory_dot", "median_ms")[1]}):
        ax.annotate("out of memory\non every phone tested", (n, 0), xytext=(0, 12), textcoords="offset points",
                    ha="center", color=INK, fontsize=8)
    limit_line(ax, LIMIT_MS, f"{LIMIT_MS} ms limit (assumption, source pending: EYKO-101)")
    axes(ax, "Search time per query, ms (median of 20)")
    ax.set_ylim(0, top * 1.15)
    ax.set_xlim(700, 450_000)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, 0.92), fontsize=8)
    ax.set_title("Vector search from memory: time per query by table size", color=INK, fontsize=10, loc="left")
    save(fig, "head2-vector-memory-speed.png")


def fig_methods(data):
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
        limit_line(ax, LIMIT_MS, f"{LIMIT_MS} ms")
        axes(ax, "ms per query (median of 20), log scale" if i == 0 else "")
        ax.set_xticks(shared, [f"{n // 1000}k" for n in shared])
        ax.set_xlim(shared[0] * 0.7, shared[-1] * 2.2)
        ax.set_title(label, color=INK, fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.suptitle("Kept in memory vs read from SQLite on every query", color=INK, fontsize=10, x=0.01, ha="left")
    save(fig, "head2-vector-memory-vs-disk.png")


def fig_heap(data):
    """The one block the vectors need (n x 512 x 4 bytes) against the heap limit, with each phone's
    measured outcome on it: a filled mark where the search ran, an x where it ran out of memory.
    Measured heap is not plotted: it includes garbage not yet collected, so it is noisy."""
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=200)
    sizes = sorted({int(r["n"]) for rows in data.values() for r in rows})
    need = {n: n * 512 * 4 / 1e6 for n in sizes}
    ax.plot(sizes, [need[n] for n in sizes], color=GRID, linewidth=6, solid_capstyle="round", zorder=1)
    ax.annotate("memory the vectors need (n × 512 × 4 bytes)", (sizes[-2], need[sizes[-2]]), xytext=(-6, 10),
                textcoords="offset points", ha="right", color=MUTED, fontsize=8)
    count = len(data)
    for i, (device, rows) in enumerate(data.items()):
        label, colour, marker = style(device, i)
        ran, failed = by_size(rows, "blob_memory_dot", "median_ms")
        shift = 1 + (i - (count - 1) / 2) * 0.06  # side by side, so both marks show at the same size
        ax.scatter([n * shift for n in ran], [need[n] for n in ran], color=colour, marker=marker, s=46,
                   edgecolors="white", linewidths=1, zorder=3, label=f"{label}: search ran")
        ax.scatter([n * shift for n in failed], [need[n] for n in failed], color=colour, marker="x", s=60,
                   linewidths=2, zorder=3, label=f"{label}: out of memory")
    worst = max(n for rows in data.values() for n in by_size(rows, "blob_memory_dot", "median_ms")[1])
    ax.annotate(f"{worst // 1000}k needs one {need[worst]:.0f} MB block:\nout of memory on every phone tested",
                (worst, need[worst]), xytext=(-12, -4), textcoords="offset points", ha="right", va="top",
                color=INK, fontsize=8)
    limit_line(ax, HEAP_LIMIT_MB, f"Java heap limit Android gives the app: {HEAP_LIMIT_MB} MB")
    axes(ax, "MB")
    ax.set_ylim(0, 680)
    ax.set_xlim(700, 450_000)
    ax.legend(frameon=False, loc="upper left", fontsize=7.5)
    ax.set_title("Memory the in-memory vectors need vs the app's heap limit", color=INK, fontsize=10, loc="left")
    save(fig, "head2-vector-heap.png")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(HERE / name, facecolor="#fcfcfb")
    plt.close(fig)
    print(f"wrote {name}")


if __name__ == "__main__":
    plt.rcParams["font.family"] = "Calibri"
    sweeps = load()
    fig_memory(sweeps)
    fig_methods(sweeps)
    fig_heap(sweeps)
