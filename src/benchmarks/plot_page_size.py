"""EYKO-167: draw the page-size trade-off from docs/results/page-size/page-size.json. Run: task page-size-plot

Three panels against the page size (no second axis): the library's size and the vector rows' bytes, the bytes one small
commit writes to the WAL, and single-row read times. Writes docs/results/page-size/page-size-tradeoff.png and .svg.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "docs/results/page-size"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
CHOSEN = "#2a78d6"  # 16 KB, the proposed size
COLOURS = ["#2a78d6", "#eb6834", "#1baf7a"]  # series order within a panel


def frame(ax, title, ylabel, pages):
    ax.set_title(title, fontsize=9, color=INK, loc="left")
    ax.set_xscale("log", base=2)
    ax.set_xticks(pages, [f"{p // 1024} KB" for p in pages])
    ax.minorticks_off()
    ax.set_xlabel("SQLite page size", color=MUTED, fontsize=8)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=8)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=7.5)
    ax.axvspan(16384 / 1.25, 16384 * 1.25, color=CHOSEN, alpha=0.08, zorder=0)


def line(ax, xs, ys, label, colour, fmt):
    ax.plot(xs, ys, color=colour, marker="o", linewidth=2, markersize=6, markeredgecolor=SURFACE, label=label, zorder=3)
    for x, y in zip(xs, ys):
        ax.annotate(fmt(y), (x, y), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7, color=INK)


def main():
    d = json.loads((DIR / "page-size.json").read_text(encoding="utf-8"))
    e1, e5 = d["e1_library_20k"], d["e5_small_writes_and_reads"]
    pages = sorted(int(p) for p in e1)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))

    ax = axes[0]
    line(ax, pages, [e1[str(p)]["file_bytes"] / 1e6 for p in pages], "whole library (MB)", COLOURS[0], lambda v: f"{v:.0f}")
    frame(ax, "Space: 20,000 kept frames, all tables", "MB on disk", pages)
    ax.set_ylim(0, 720)
    ax.legend(fontsize=7, frameon=False, loc="upper right")

    ax = axes[1]
    wp = sorted(int(p) for p in e5)
    line(ax, wp, [e5[str(p)]["wal_bytes_per_commit"] / 1e3 for p in wp], "WAL bytes per commit (kB)", COLOURS[1], lambda v: f"{v:.0f}")
    frame(ax, "Cost: one relink-style commit (3 sightings)", "kB written to the WAL", wp)
    ax.set_ylim(0, 520)
    ax.legend(fontsize=7, frameon=False, loc="upper left")

    ax = axes[2]
    for (key, label), colour in zip((("sighting_by_id", "sighting by id"), ("scene_by_frame", "scene record by frame")), COLOURS[:2]):
        line(ax, wp, [e5[str(p)]["read_ms"][key] * 1e3 for p in wp], label, colour, lambda v: f"{v:.1f}")
    frame(ax, "Cost: one single-row read", "µs per read", wp)
    ax.set_ylim(0, 22)
    ax.legend(fontsize=7, frameon=False, loc="upper left")

    fig.text(0.01, 0.985, "SQLite page size: 16 KB takes almost all the space saving at the lowest cost (EYKO-167)",
             ha="left", va="top", fontsize=11, color=INK, fontweight="bold")
    fig.text(0.01, 0.925, "Laptop, SQLite 3.37.2, the app's real table design with real MobileCLIP vectors, WAL mode as on the phone. "
             "Shaded: 16 KB, the proposed size. Data: docs/results/page-size/page-size.json (src/benchmarks/vector_page_size.py).",
             ha="left", va="top", fontsize=8, color=MUTED, wrap=True)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    for ext in ("png", "svg"):
        fig.savefig(DIR / f"page-size-tradeoff.{ext}", dpi=170, facecolor=SURFACE)
    plt.close(fig)
    print("wrote docs/results/page-size/page-size-tradeoff.png and .svg")


if __name__ == "__main__":
    main()
