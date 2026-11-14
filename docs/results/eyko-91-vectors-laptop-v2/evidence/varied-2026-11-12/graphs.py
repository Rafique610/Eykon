"""EYKO-91 step 5: S1 random + S2 phone-real (7 Nov, 1k-300k) beside S3 varied COCO (12 Nov, 1k-100k).

A quick look for the write-up; the official figures are EYKO-97. Adapted from ../full-2026-11-07/full_graphs.py.
"""
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FixedLocator, NullLocator  # noqa: E402

RESULTS, OUT = Path(sys.argv[1]), Path(sys.argv[2])
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
STAMP = ("Laptop i5-10310U, plugged in · S1 + S2: 7 Nov 2026, commit 243bd98 · "
         "S3: 12 Nov 2026, commit fe17d8d, 100k COCO train2017 photos (MobileCLIP-S2), caption queries")
SIZES = [1000, 5000, 20000, 50000, 100000, 300000]
SIZE_LABELS = ["1k", "5k", "20k", "50k", "100k", "300k"]
SOURCES = {"random": "S1 · random vectors", "real": "S2 · phone-real (90 clips + tiny noise)",
           "varied": "S3 · varied real photos (COCO, up to 100k)"}
FILES = {"random": "laptop-2026-11-07-sweep.csv", "real": "laptop-2026-11-07-sweep-real.csv",
         "varied": "laptop-2026-11-12-sweep-varied.csv"}


def load(source):
    name = FILES[source]
    by = defaultdict(list)
    for r in csv.DictReader((RESULTS / name).open()):
        by[(r["method"], int(r["n"]))].append(r)
    return by


DATA = {s: load(s) for s in SOURCES}


def note(r):
    return dict(kv.split("=", 1) for kv in r["note"].split("; "))


def series(by, method, value):
    xs, ys = [], []
    for n in SIZES:
        if (method, n) in by:
            xs.append(n)
            ys.append(value(by[(method, n)]))
    return xs, ys


def median_ms(rs):
    return statistics.median(float(r["median_ms"]) for r in rs)


def recall(rs):
    return statistics.mean(float(r["recall_at_20"]) for r in rs)


def held_mb(rs):
    nt = note(rs[0])
    return int(nt["pss_after_mb"]) - int(nt["pss_before_mb"])


def last_size(by):
    return max(n for _, n in by)


def style(ax, logy=True, last=300000):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.set_xscale("log")
    shown = [n for n in SIZES if n <= last]
    ax.xaxis.set_major_locator(FixedLocator(shown))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticklabels(SIZE_LABELS[:len(shown)])
    ax.set_xlim(800, last * 3.2)
    if logy:
        ax.set_yscale("log")
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("vectors stored", color=INK2, fontsize=9)


def lines(ax, by, spec, value, fmt):
    ends = []
    for method, label, color in spec:
        xs, ys = series(by, method, value)
        ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=label, zorder=3)
        if xs[-1] < last_size(by):
            ax.annotate(f"{label}  {fmt(ys[-1])}", (xs[-1], ys[-1]), xytext=(-6, 9), textcoords="offset points",
                        ha="right", fontsize=8.5, color=INK)
        else:
            ends.append([ys[-1], xs[-1], label, fmt(ys[-1])])
    return ends


def end_labels(ax, ends, min_gap, log=True, cap=None):
    """Direct labels at each line's end, nudged apart so they never overlap."""
    import math
    key = (lambda v: math.log10(v)) if log else (lambda v: v)
    back = (lambda v: 10 ** v) if log else (lambda v: v)
    ends.sort(key=lambda e: key(e[0]))
    placed = []
    for y, x, label, text in ends:
        k = key(y)
        if placed and k - placed[-1] < min_gap:
            k = placed[-1] + min_gap
        placed.append(k)
    if cap is not None:  # stack pushed past the top: slide it back down, keeping the gaps
        for i in range(len(placed) - 1, -1, -1):
            placed[i] = min(placed[i], cap if i == len(placed) - 1 else placed[i + 1] - min_gap)
    for (y, x, label, text), k in zip(ends, placed):
        ax.annotate(f"{label}  {text}", (x, y), xytext=(x * 1.12, back(k)), fontsize=8.5, color=INK,
                    va="center", arrowprops=dict(arrowstyle="-", color=GRID, linewidth=0.8))


def finish(fig, name, title, subtitle):
    fig.suptitle(title, x=0.01, y=1.02, ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.01, 0.975, subtitle, ha="left", fontsize=9.5, color=INK2)
    fig.text(0.01, -0.09, STAMP, fontsize=8.5, color=INK2, ha="left", va="top")
    fig.savefig(OUT / name, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


# 1 · time per search against size (both sources: they barely differ for exact methods)
TIME = [("blob_memory_pyloop", "Python loop", RED), ("blob_disk_dot", "read from DB each search", VIOLET),
        ("sqlite_vec_f32", "sqlite-vec f32", YELLOW), ("blob_memory_f16", "float16", AQUA),
        ("usearch_exact_f32", "usearch exact", MAGENTA), ("blob_memory_i8_rescore", "int8 + re-check", ORANGE),
        ("blob_memory_numpy_1t", "numpy f32, 1 thread", BLUE), ("usearch_hnsw_c32_ef1024", "HNSW c32/ef1024", GREEN)]
fig, axes = plt.subplots(1, 3, figsize=(22, 6.4), facecolor=SURFACE, sharey=True)
for ax, (source, title) in zip(axes, SOURCES.items()):
    ends = lines(ax, DATA[source], TIME, median_ms, lambda v: f"{v:.0f} ms" if v >= 10 else f"{v:.1f} ms")
    end_labels(ax, ends, 0.13)
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    style(ax, last=last_size(DATA[source]))
    ax.set_ylim(0.03, 1500)
axes[0].set_ylabel("median time per search (ms, log scale)", color=INK2, fontsize=9)
axes[0].text(1000, 0.04, "DB-read and Python loop are only run up to 20k", fontsize=8.5, color=INK2)
fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=8, frameon=False, fontsize=8.5, labelcolor=INK)
finish(fig, "1-time-vs-size.png", "Time per search as the library grows (lower is faster)",
       "Median of 5 runs × 20 searches, one CPU thread. Exact search grows in step with size; HNSW stays nearly flat.")

# 2 · recall against size, approximate methods only (exact ones are 1.0 at every size)
RECALL = [("blob_memory_i8_rescore", "int8 + re-check", ORANGE), ("blob_memory_f16", "float16", AQUA),
          ("blob_memory_i8", "int8 alone", BLUE), ("sqlite_vec_int8", "sqlite-vec int8", YELLOW),
          ("usearch_hnsw_c32_ef1024", "HNSW c32/ef1024", GREEN), ("usearch_hnsw_c16_ef256", "HNSW c16/ef256", VIOLET),
          ("usearch_hnsw_c16_ef64", "HNSW c16/ef64 (default)", MAGENTA)]
fig, axes = plt.subplots(1, 3, figsize=(23, 6.4), facecolor=SURFACE, sharey=True, gridspec_kw={"wspace": 0.42})
for ax, (source, title) in zip(axes, SOURCES.items()):
    last = last_size(DATA[source])
    ends = lines(ax, DATA[source], RECALL, recall, lambda v: f"{v:.2f}")
    end_labels(ax, ends, 0.055, log=False, cap=1.0)
    ax.hlines(0.95, 800, last * 1.1, color=INK2, linewidth=1, linestyle=(0, (4, 3)), zorder=2)
    ax.text(900, 0.935, "0.95 pass mark", fontsize=8.5, color=INK2, va="top")
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    style(ax, logy=False, last=last)
    ax.set_ylim(-0.02, 1.04)
axes[0].set_ylabel("recall@20 (share of the true top 20 found)", color=INK2, fontsize=9)
axes[1].text(1000, 0.17, "S2 copies each clip ~3,300× at 300k:\nfinding the true top 20 among\nnear-twins is HNSW's worst case",
             fontsize=8.5, color=INK2)
axes[2].text(1000, 0.17, "100,000 distinct real photos:\nHNSW c16/ef64 falls from 1.00 at 1k\nto the 0.95 mark at 100k",
             fontsize=8.5, color=INK2)
fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=7, frameon=False, fontsize=8.5, labelcolor=INK)
finish(fig, "2-recall-vs-size.png", "Accuracy as the library grows (higher is better; all exact methods stay at 1.0)",
       "Mean over 5 runs × 20 searches. int8 + re-check stays at 1.0 on every source; sqlite-vec int8 is below the mark on real photos.")

# 3 · memory held against size (S3 varied; S1 random is in ../full-2026-11-07)
MEM = [("blob_memory_pyloop", "Python loop", RED), ("usearch_hnsw_c32_ef1024", "HNSW c32/ef1024", GREEN),
       ("usearch_exact_f32", "usearch exact", MAGENTA), ("blob_memory_numpy_1t", "numpy f32", BLUE),
       ("blob_memory_f16", "float16", AQUA), ("blob_memory_i8_rescore", "int8 + re-check", ORANGE),
       ("sqlite_vec_f32", "sqlite-vec f32 *", YELLOW)]
fig, ax = plt.subplots(figsize=(11, 6.6), facecolor=SURFACE)
ends = lines(ax, DATA["varied"], MEM, lambda rs: max(held_mb(rs), 1), lambda v: f"{v:.0f} MB")
S3_SIZES = SIZES[:-1]
ax.plot(S3_SIZES, [n * 512 * 4 / 2**20 for n in S3_SIZES], color=INK2, linewidth=1, linestyle=(0, (4, 3)), zorder=2)
ax.text(1100, 1000 * 512 * 4 / 2**20 * 1.25, "the float32 vectors themselves", fontsize=8.5, color=INK2, rotation=0)
end_labels(ax, ends, 0.1)
style(ax, last=last_size(DATA["varied"]))
ax.set_ylim(0.8, 2500)
ax.set_ylabel("memory held after building (MB, log scale)", color=INK2, fontsize=9)
ax.text(1100, 1300, "* sqlite-vec keeps its data in the database file (the OS file cache),\n  which this measure does not count",
        fontsize=8.5, color=INK2, va="top")
ax.legend(loc="lower right", frameon=False, fontsize=8.5, labelcolor=INK)
finish(fig, "3-memory-vs-size.png", "Memory each method holds as the library grows (lower is smaller)",
       "PSS after building minus PSS before, S3 varied COCO photos. int8 + re-check holds under a third of float32.")
print("written", sorted(p.name for p in OUT.glob("*-vs-size.png")))
