# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["matplotlib==3.9.2"]
# ///
"""Head 7 graphs: the app's real search (VideoSearch.frames) before and after EYKO-102.

Reads docs/results/vectors/search/*-search-before.csv and *-search-after.csv and redraws the same
PNGs next to this file. A phone without an "after" file is drawn with its "before" line only.

Run from the repo root:  uv run docs/documents/source/figures/search_speed.py
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
RESULTS = HERE.parents[2] / "results" / "vectors" / "search"
LIMIT_MS = 200
PHONES = {"samsung SM-A325F": ("Samsung A32", "#2a78d6", "o"), "Google Pixel 9 Pro XL": ("Pixel 9 Pro XL", "#eb6834", "s")}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def load():
    """{device: {"before": rows, "after": rows}} from the newest file of each kind per phone."""
    data = defaultdict(dict)
    for kind in ("before", "after"):
        for path in sorted(RESULTS.glob(f"*-search-{kind}.csv")):
            rows = list(csv.DictReader(path.open(encoding="utf-8")))
            data[rows[0]["device"]][kind] = rows
            print(f"using: {path.name}")
    return {d: data[d] for d in PHONES if d in data}


def medians(rows, method):
    """{n: median of the run medians} for one method."""
    runs = defaultdict(list)
    for r in rows:
        if r["method"] == method and r["median_ms"]:
            runs[int(r["n"])].append(float(r["median_ms"]))
    return {n: statistics.median(v) for n, v in sorted(runs.items())}


def style_axes(ax, ylabel):
    ax.set_xscale("log")
    ax.set_xlabel("Kept frames (+12 dropped each)", color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.minorticks_off()


def fig_before_after(data):
    fig, panels = plt.subplots(1, len(data), figsize=(7.2, 3.8), dpi=200, sharey=True)
    panels = panels if len(data) > 1 else [panels]
    top = max(max(medians(k["before"], "app_search_frames").values()) for k in data.values())
    for i, (ax, (device, kinds)) in enumerate(zip(panels, data.items())):
        label, colour, marker = PHONES[device]
        for kind, c, name in (("before", MUTED, "before (the app until EYKO-102)"), ("after", colour, "after (same hits)")):
            if kind not in kinds:
                continue
            m = medians(kinds[kind], "app_search_frames")
            ax.plot(list(m), list(m.values()), color=c, marker=marker, markersize=6, linewidth=2,
                    markeredgecolor="white", markeredgewidth=1, label=name)
            last = list(m)[-1]
            value = m[last]
            ax.annotate(f"{value / 1000:.1f} s" if value >= 1000 else f"{value:.0f} ms", (last, value), xytext=(6, -3),
                        textcoords="offset points", fontsize=8, color=INK)
        ax.axhline(LIMIT_MS, color=MUTED, linestyle=(0, (4, 3)), linewidth=1)
        ax.annotate(f"{LIMIT_MS} ms", (0.01, LIMIT_MS), xycoords=("axes fraction", "data"), xytext=(0, 4),
                    textcoords="offset points", color=MUTED, fontsize=8)
        style_axes(ax, "ms per search (median of 20 queries)" if i == 0 else "")
        sizes = list(medians(kinds["before"], "app_search_frames"))
        ax.set_xticks(sizes, [f"{n // 1000}k" for n in sizes])
        ax.set_xlim(sizes[0] * 0.7, sizes[-1] * 1.9)
        ax.set_ylim(0, top * 1.12)
        ax.set_title(label, color=INK, fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.suptitle("The app's search, end to end: before and after EYKO-102", color=INK, fontsize=10, x=0.01, ha="left")
    save(fig, "head7-search-before-after.png")


def fig_split(data):
    """Before EYKO-102 only: where one search's time went, the vector part (the search called knn
    for every row) and everything else. After the change the search no longer calls knn, so
    knn's time is not its vector part any more and is not drawn."""
    fig, panels = plt.subplots(1, len(data), figsize=(7.2, 3.8), dpi=200, sharey=True)
    panels = panels if len(data) > 1 else [panels]
    for i, (ax, (device, kinds)) in enumerate(zip(panels, data.items())):
        label, colour, _ = PHONES[device]
        bars, names = [], []
        total, vec = medians(kinds["before"], "app_search_frames"), medians(kinds["before"], "app_knn_all")
        for n in total:
            bars.append((vec[n], max(total[n] - vec[n], 0)))
            names.append(f"{n // 1000}k")
            ax.annotate(f"{vec[n] / total[n]:.0%} vectors", (len(bars) - 1, total[n]), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=7, color=INK)
        x = range(len(bars))
        ax.bar(x, [b[0] for b in bars], color=colour, width=0.7, edgecolor="#fcfcfb", linewidth=1, label="vector part (knn)")
        ax.bar(x, [b[1] for b in bars], bottom=[b[0] for b in bars], color=GRID, width=0.7, edgecolor="#fcfcfb",
               linewidth=1, label="everything else (frames query, ranking, windows)")
        ax.set_xticks(list(x), names, fontsize=8)
        ax.set_xlabel("Kept frames (before the change)", color=MUTED)
        ax.set_ylabel("ms per search" if i == 0 else "", color=MUTED)
        ax.grid(True, axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=MUTED)
        ax.set_title(label, color=INK, fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.suptitle("Before the change: where one search's time went", color=INK, fontsize=10, x=0.01, ha="left")
    save(fig, "head7-search-split.png")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(HERE / name, facecolor="#fcfcfb")
    plt.close(fig)
    print(f"wrote {name}")


if __name__ == "__main__":
    plt.rcParams["font.family"] = "Calibri"
    phones = load()
    fig_before_after(phones)
    fig_split(phones)
