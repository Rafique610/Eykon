"""EYKO-123: Head 3 intake, two phones side by side. Median seconds per stage per phone, from docs/results/head3/stage_times.csv.

  uv run python src/benchmarks/head3_compare.py --pair "Infinix X670:1,2,3" --pair "Pixel 9 Pro XL:1,2,3" --label "clip 1" \
      --pair "Infinix X670:4,5,6" --pair "Pixel 9 Pro XL:4,5,6" --label "clip 2" --png docs/results/head3/stage_medians_S1_two_phones.png

Each --label closes one panel made of the --pair options before it (phone:runs, S1 only). Prints a markdown table and writes one chart.
"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from head3_intake import STAGE_ORDER, chart_rows  # noqa: E402

COLOURS = ["#2a78d6", "#eb6834"]  # categorical slots 1-2 of the dataviz default palette, validated (light surface)


def medians(csv_path: Path, phone: str, runs: list[str]) -> dict[str, float]:
    by: dict[str, list[float]] = {}
    for r in chart_rows(csv_path, "S1", runs, phone):
        by.setdefault(r["stage"], []).append(int(r["ms"]) / 1000)
    return {s: statistics.median(v) for s, v in by.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="docs/results/head3/stage_times.csv")
    ap.add_argument("--pair", action="append", default=[], help="phone:runs, e.g. 'Pixel 9 Pro XL:1,2,3'")
    ap.add_argument("--label", action="append", default=[], help="closes a panel; the pairs given before it belong to it")
    ap.add_argument("--png", required=True)
    # argparse loses the order of mixed options, so read panels straight from argv
    a = ap.parse_args()
    panels, current, argv = [], [], sys.argv[1:]
    for i, tok in enumerate(argv):
        if tok == "--pair":
            phone, runs = argv[i + 1].rsplit(":", 1)
            current.append((phone, runs.split(",")))
        elif tok == "--label":
            panels.append((argv[i + 1], current))
            current = []

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(panels), figsize=(6.5 * len(panels), 5), sharey=True, sharex=True, facecolor="#fcfcfb")
    axes = axes if len(panels) > 1 else [axes]
    for ax, (label, pairs) in zip(axes, panels):
        meds = [(phone, medians(Path(a.csv), phone, runs)) for phone, runs in pairs]
        stages = [s for s in STAGE_ORDER if any(s in m for _, m in meds) and s not in ("copy", "hash")]
        print(f"\n{label}\n\n| Stage | " + " | ".join(p for p, _ in meds) + " |\n|---|" + "---|" * len(meds))
        for s in stages:
            print(f"| {s} | " + " | ".join(f"{m.get(s, 0):.1f}" for _, m in meds) + " |")
        print("| **added up** | " + " | ".join(f"**{sum(m.get(s, 0) for s in stages):.1f}**" for _, m in meds) + " |")
        h = 0.38
        y = range(len(stages))
        for k, (phone, m) in enumerate(meds):
            vals = [m.get(s, 0) for s in stages]
            bars = ax.barh([i + (k - 0.5) * h for i in y], vals, height=h - 0.04, color=COLOURS[k], label=phone)
            ax.bar_label(bars, labels=[f"{v:.0f}" if v >= 5 else "" for v in vals], padding=3, fontsize=8, color="#52514e")
        ax.set_yticks(list(y), stages)
        ax.set_title(f"S1, {label}: median seconds per stage", color="#0b0b0b", fontsize=11, loc="left")
        ax.set_xlabel("seconds (median of 3 runs, plugged in)", color="#52514e")
        ax.set_facecolor("#fcfcfb")
        ax.grid(axis="x", color="#e6e5e1", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].invert_yaxis()  # shared y: invert once, so the stages read top to bottom in pipeline order
    axes[0].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(a.png, dpi=150, facecolor=fig.get_facecolor())
    print("\nwrote", a.png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
