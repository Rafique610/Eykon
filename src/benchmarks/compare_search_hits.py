"""Compare the app's search hits before and after a change (EYKO-102).

Each line of a hits file is: query  frame_id  window_start_s  window_end_s  score
(written by VideoSearchSpeedTest on the phone). Frames and windows must be identical in the same
order; scores may differ only in the last digits (tolerance 1e-5), because adding the dot product in
four sums changes the order of the additions.

    uv run --no-project python src/benchmarks/compare_search_hits.py docs/results/vectors/search
"""
import sys
from pathlib import Path


def read(path: Path) -> list[tuple[str, str, str, str, float]]:
    rows = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            q, frame, start, end, score = line.split()
            rows.append((q, frame, start, end, float(score)))
    return rows


def compare(before: Path, after: Path) -> tuple[int, int, float]:
    """(hits compared, hits that differ, largest score difference)."""
    a, b = read(before), read(after)
    differ = abs(len(a) - len(b))
    worst = 0.0
    for x, y in zip(a, b):
        worst = max(worst, abs(x[4] - y[4]))
        if x[:4] != y[:4] or abs(x[4] - y[4]) > 1e-5:
            differ += 1
    return max(len(a), len(b)), differ, worst


if __name__ == "__main__":
    folder = Path(sys.argv[1])
    for before in sorted(folder.glob("*-hits-before-*.txt")):
        after = before.with_name(before.name.replace("-before-", "-after-"))
        if not after.exists():
            print(f"{before.name}: no after file yet")
            continue
        total, differ, worst = compare(before, after)
        verdict = "IDENTICAL" if differ == 0 else "DIFFERENT"
        print(f"{before.name.replace('-hits-before', '')}: {verdict}, {total} hits, {differ} differ, largest score change {worst:.1e}")
