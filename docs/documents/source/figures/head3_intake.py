# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["matplotlib==3.9.2"]
# ///
"""Head 3 graphs for head3-defense.js, redrawn next to this file.

- head3-stage-times.png  median seconds per stage, S1, Pixel and Infinix (src/benchmarks/head3_compare.py on head3/stage_times.csv)
- head3-work-per-minute.png  minutes of work per minute of video, every run in head3/run_summary.csv
- head3-background.png  time to ready with the app in front and in the background (numbers from the EYKO-44 and EYKO-85 result files)
- head3-latest-profile.png  copy of docs/results/latest-profile/latest-time-vs-sightings.png (EYKO-120, drawn by src/benchmarks/latest_profile.py)

Run from the repo root:  uv run docs/documents/source/figures/head3_intake.py
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
REPO = HERE.parents[3]
RESULTS = REPO / "docs" / "results"
PHONES = {"Pixel 9 Pro XL": "#eb6834", "Infinix X670": "#2a78d6", "SM-A325F": "#1baf7a"}  # same slots as head3_compare.py (A32 = SM-A325F)
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)


def stage_times():
    out = HERE / "head3-stage-times.png"
    subprocess.run([sys.executable, str(REPO / "src" / "benchmarks" / "head3_compare.py"),
                    "--csv", str(RESULTS / "head3" / "stage_times.csv"),
                    "--pair", "Infinix X670:1,2,3", "--pair", "Pixel 9 Pro XL:1,2,3", "--pair", "SM-A325F:1,2,3", "--label", "clip 1",
                    "--pair", "Infinix X670:4,5,6", "--pair", "Pixel 9 Pro XL:4,5,6", "--pair", "SM-A325F:4,5,6", "--label", "clip 2",
                    "--png", str(out)], check=True, stdout=subprocess.DEVNULL)
    print("wrote", out.name)


def work_per_minute():
    """One dot per run: S1 clip 1 (runs 1-3 and the Pixel's unplugged 7-9), S1 clip 2 (runs 4-6), S2 queue."""
    rows = list(csv.DictReader((RESULTS / "head3" / "run_summary.csv").open(encoding="utf-8")))
    groups = [("S1, clip 1", lambda r: r["scenario"] == "S1" and r["run"] in ("1", "2", "3", "7", "8", "9")),
              ("S1, clip 2", lambda r: r["scenario"] == "S1" and r["run"] in ("4", "5", "6")),
              ("S2, queue of 9-10", lambda r: r["scenario"] == "S2")]
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=SURFACE)
    for gi, (label, pick) in enumerate(groups):
        for pi, (phone, colour) in enumerate(PHONES.items()):
            vals = [float(r["work_s_per_video_s"]) for r in rows if r["phone"] == phone and pick(r)]
            y = gi + (pi - (len(PHONES) - 1) / 2) * 0.26
            ax.scatter(vals, [y] * len(vals), s=64, color=colour, edgecolor=SURFACE, linewidth=2, zorder=3,
                       label=phone if gi == 0 else None)
            if vals:
                ax.text(max(vals) + 0.06, y, f"{min(vals):.2f}-{max(vals):.2f}" if len(vals) > 1 else f"{vals[0]:.2f}",
                        va="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(groups)), [g[0] for g in groups])
    ax.invert_yaxis()
    ax.set_xlim(0, 5.2)
    ax.axvline(1, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.text(1.03, 0.5, "1 = as long as the video", fontsize=8, color=MUTED, va="center")
    ax.set_xlabel("minutes of work per minute of video (app in front)", color=MUTED)
    ax.set_title("Work per minute of video, every harness run (EYKO-117, EYKO-123)", color=INK, fontsize=11, loc="left")
    style(ax)
    ax.legend(frameon=False, loc="lower right", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(HERE / "head3-work-per-minute.png", dpi=150, facecolor=SURFACE)
    print("wrote head3-work-per-minute.png")


def background():
    """Minutes from adding the clip to ready. Sources in the subtitle; each panel is one clip on one phone."""
    panels = [
        ("Infinix X670, 5-min clip (EYKO-44, 12 Nov)", PHONES["Infinix X670"], [
            ("app in front (A)", 329 / 60), ("5 other apps in front (B)", 404 / 60), ("swiped from recents (C)", 326 / 60)]),
        ("Pixel 9 Pro XL, 8-min clip (EYKO-85, 15 Nov)", PHONES["Pixel 9 Pro XL"], [
            ("Home, screen off, deep Doze", 250 / 60), ("same, Battery Saver on", 244 / 60)]),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), facecolor=SURFACE, sharex=True)
    for ax, (title, colour, bars) in zip(axes, panels):
        labels, vals = zip(*bars)
        b = ax.barh(range(len(vals)), vals, height=0.55, color=colour)
        ax.bar_label(b, labels=[f"{v:.1f} min" for v in vals], padding=4, fontsize=8.5, color=MUTED)
        ax.set_yticks(range(len(vals)), labels)
        ax.invert_yaxis()
        ax.set_title(title, color=INK, fontsize=10, loc="left")
        ax.set_xlabel("minutes from adding the clip to ready", color=MUTED)
        style(ax)
    axes[0].set_xlim(0, 8.5)
    fig.tight_layout()
    fig.savefig(HERE / "head3-background.png", dpi=150, facecolor=SURFACE)
    print("wrote head3-background.png")


def latest_profile():
    src = RESULTS / "latest-profile" / "latest-time-vs-sightings.png"
    shutil.copyfile(src, HERE / "head3-latest-profile.png")
    print("copied head3-latest-profile.png from", src.relative_to(REPO))


if __name__ == "__main__":
    stage_times()
    work_per_minute()
    background()
    latest_profile()
