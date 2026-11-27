# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["matplotlib==3.9.2"]
# ///
"""Head 4 graph: moments found by each keyframe method at the same number of frames, on three data sets.

Reads the saved result tables in docs/results/ (nothing is re-run) and redraws head4-methods.png next to this file:
  six short own clips  : 2026-10-13-keyframes-slots-on-phone.md (ours, evenly spaced, PySceneDetect, ffmpeg) + keyframes/katna-six-clips-2026-11-27.md
  long still clips     : keyframes/score-still-2026-11-26.md (Pixel run) + keyframes/katna-still-2026-11-27.md
  EPIC-KITCHENS-100    : keyframes/katna-epic-2026-11-27.md (ours = laptop copy) + keyframes/uniform-epic-2026-11-27.md

Run from the repo root:  uv run docs/documents/source/figures/head4_keyframes.py
"""
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
RESULTS = HERE.parents[2] / "results"
KF = RESULTS / "keyframes"
# fixed method order and colour (categorical slots 1-5 of the reference palette), the same in every panel
METHODS = [("Ours", "#2a78d6"), ("Evenly spaced", "#eb6834"), ("PySceneDetect", "#1baf7a"), ("ffmpeg scene", "#eda100"), ("Katna", "#e87ba4")]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def rows(path: Path) -> list[list[str]]:
    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("|")]


def first(table, starts: str) -> list[str]:
    return next(r for r in table if r[0].startswith(starts))


def hits(cell: str) -> int:
    return int(re.match(r"\**(\d+)", cell).group(1))


def katna(path: Path) -> tuple[int, int, int]:
    """(Katna hit, ours hit, moments) from the **all** row of keyframe_katna.py's table."""
    r = first(rows(path), "**all**")
    return hits(r[3]), hits(r[4]), int(r[5])


def six() -> dict:
    t = rows(RESULTS / "2026-10-13-keyframes-slots-on-phone.md")
    k, _, total = katna(KF / "katna-six-clips-2026-11-27.md")
    return dict(title="Six short own clips", note="44 frames · ours = Pixel", total=total, values={
        "Ours": int(first(t, "Ours, now")[4]), "Evenly spaced": int(first(t, "B0 uniform")[4]),
        "PySceneDetect": int(first(t, "B3 PySceneDetect content")[4]), "ffmpeg scene": int(first(t, "B2 ffmpeg")[4]), "Katna": k})


def still() -> dict:
    t = rows(KF / "score-still-2026-11-26.md")
    k, _, total = katna(KF / "katna-still-2026-11-27.md")
    hit = lambda starts: int(first(t, starts)[3].split(" of ")[0])  # noqa: E731
    return dict(title="Two long, mostly still clips", note="59 frames · ours = Pixel", total=total, values={
        "Ours": hit("ours"), "Evenly spaced": hit("B0 uniform"),
        "PySceneDetect": hit("B3 PySceneDetect content"), "ffmpeg scene": hit("B2 ffmpeg"), "Katna": k})


def epic() -> dict:
    k, ours, total = katna(KF / "katna-epic-2026-11-27.md")
    u = hits(first(rows(KF / "uniform-epic-2026-11-27.md"), "**all**")[2])
    return dict(title="EPIC-KITCHENS-100", note="175 frames · ours = laptop copy", total=total,
                values={"Ours": ours, "Evenly spaced": u, "Katna": k})


def main() -> None:
    sets = [six(), still(), epic()]
    plt.rcParams.update({"font.family": "Arial", "font.size": 10, "text.color": INK, "axes.labelcolor": MUTED,
                         "xtick.color": MUTED, "ytick.color": INK})
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True, facecolor=SURFACE)
    names = [m for m, _ in METHODS]
    for ax, s in zip(axes, sets):
        ax.set_facecolor(SURFACE)
        for i, (name, colour) in enumerate(METHODS):
            if name not in s["values"]:
                ax.text(1, i, "not run at this budget", va="center", fontsize=8.5, color=MUTED)
                continue
            v = s["values"][name]
            share = 100 * v / s["total"]
            ax.barh(i, share, height=0.62, color=colour, edgecolor=SURFACE, linewidth=2)
            ax.text(share + 1.5, i, f"{v} of {s['total']}", va="center", fontsize=9, color=INK,
                    fontweight="bold" if name == "Ours" else "normal")
        ax.set_xlim(0, 118)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0", "25", "50", "75", "100 %"])
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(axis="y", length=0)
        ax.set_title(f"{s['title']}\n", fontsize=10.5, fontweight="bold", loc="left", color=INK)
        ax.text(0, 1.02, s["note"], transform=ax.transAxes, fontsize=8.5, color=MUTED)
    axes[0].set_yticks(range(len(names)))
    axes[0].set_yticklabels(names)
    axes[0].invert_yaxis()
    axes[1].set_xlabel("share of marked moments with a sharp kept frame, every method at the same frame count")
    fig.tight_layout()
    out = HERE / "head4-methods.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(out, {s["title"]: s["values"] for s in sets})


if __name__ == "__main__":
    main()
