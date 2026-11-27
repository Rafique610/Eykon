"""How sure are the Ego4D scores? 95 % intervals and the strongest test the saved files allow. Run: task score-intervals

Every score in docs/results/ego4d/*.json is a share of n questions (or action instances). This reads those files,
turns each share back into a count, and prints:
  - a Wilson 95 % interval for each reported score (the usual interval for a share of a small n);
  - for each "before -> after" change we adopted, the BEST-CASE exact McNemar test. The saved files keep only totals,
    not which question passed, so the most favourable case is assumed: every question that passed before still
    passes after, so all (after - before) differences are wins. That gives the smallest p any real split could give.
    If even that p is above 0.05, the files cannot show the change is real. If it is below, the change MAY be real
    and needs the per-question results to be sure.
No Ego4D video or annotation is read: only our own saved totals (licence, EYKO-139).
Writes docs/results/score-intervals/score-intervals.json.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "docs/results/ego4d"
OUT = ROOT / "docs/results/score-intervals"


def load(name):
    return json.loads((E / f"{name}.json").read_text(encoding="utf-8"))


def count(pct, n):
    """The saved scores are rounded to 0.1 %, so the count is the nearest whole number."""
    return round(pct * n / 100)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(100 * (mid - half), 1), round(100 * (mid + half), 1)


def best_case_mcnemar(k_before, k_after):
    """Exact two-sided McNemar p when all differences are wins: b = |after - before| discordant pairs, c = 0."""
    b = abs(k_after - k_before)
    return 1.0 if b == 0 else min(1.0, 2 * 0.5 ** b)


def main():
    rows, changes = [], []

    def score(where, what, pct, n):
        k = count(pct, n)
        lo, hi = wilson(k, n)
        rows.append({"where": where, "score": what, "pct": pct, "k": k, "n": n, "ci95": [lo, hi]})
        return k

    def change(card, what, set_, before, after, n):
        kb, ka = count(before, n), count(after, n)
        p = best_case_mcnemar(kb, ka)
        changes.append({"card": card, "change": what, "set": set_, "n": n, "before": [before, kb, wilson(kb, n)],
                        "after": [after, ka, wilson(ka, n)], "best_case_p": round(p, 4),
                        "verdict": "not shown (even the best case p > 0.05)" if p > 0.05 else "may be real (best case p <= 0.05); needs per-question results"})

    # NLQ objects: windows (EYKO-58), app default grow 0.85
    for set_, f in (("A", "windows-A-2026-10-20"), ("B", "windows-B-2026-10-21")):
        o = load(f)["nlq"]["objects"]
        n = o["n"]
        for m in ("R@1 0.3", "R@1 0.5", "R@5 0.3", "R@5 0.5"):
            score(f"NLQ objects set {set_}", f"frame {m}", o[f"frame {m}"], n)
            score(f"NLQ objects set {set_}", f"grow 0.85 {m}", o[f"grow 0.85 {m}"], n)
            change("EYKO-58", f"windows grow 0.85, {m}", set_, o[f"frame {m}"], o[f"grow 0.85 {m}"], n)
        score(f"NLQ objects set {set_}", "hit@1", o["hit@1"], n)
        # the grow setting was chosen between 0.95 / 0.9 / 0.85 / 0.8 on set A: how far apart are they?
        for g in ("0.9", "0.8"):
            change("EYKO-58 (choice)", f"grow {g} -> 0.85, R@1 0.3", set_, o[f"grow {g} R@1 0.3"], o["grow 0.85 R@1 0.3"], n)

    # VQ last seen (EYKO-62): app crops -> any-object crops, cut-off 0.87
    for set_ in ("A", "B"):
        d = load(f"lastseen-{set_}")
        n = d["queries"]
        app, anything = d["app mobileclip T0.87"]["success"], d["anything mobileclip T0.87"]["success"]
        score(f"VQ last seen set {set_}", "app crops success", app, n)
        score(f"VQ last seen set {set_}", "any-object crops success", anything, n)
        change("EYKO-62", "any-object crops, success", set_, app, anything, n)

    # MQ actions (EYKO-60): app prompts -> wearer prompts, smoothing 6 s ("found" is a share of instances)
    for set_ in ("A", "B"):
        d = load(f"actions-{set_}")
        before, after = d["app smooth 0 floor 0.30"]["summary"], d["wearer smooth 6 floor 0.30"]["summary"]
        n = before["instances"]
        score(f"MQ actions set {set_}", "found, app prompts", before["found"], n)
        score(f"MQ actions set {set_}", "found, wearer prompts + 6 s", after["found"], n)
        change("EYKO-60", "wearer prompts + smoothing 6 s, found", set_, before["found"], after["found"], n)
        no_smooth = d["wearer smooth 0 floor 0.30"]["summary"]
        change("EYKO-60 (smoothing)", "smoothing 0 -> 6 s, R@1 tIoU 0.5", set_, no_smooth["R@1 tIoU>=0.5"], after["R@1 tIoU>=0.5"], n)

    # Sets A and B pooled (different questions, same method): more questions, a stronger best case
    pooled = {}
    for c in changes:
        key = (c["card"], c["change"])
        a = pooled.setdefault(key, [0, 0, 0])
        a[0] += c["before"][1]; a[1] += c["after"][1]; a[2] += c["n"]
    for (card, what), (kb, ka, n) in pooled.items():
        p = best_case_mcnemar(kb, ka)
        changes.append({"card": card, "change": what, "set": "A+B", "n": n, "before": [round(100 * kb / n, 1), kb, wilson(kb, n)],
                        "after": [round(100 * ka / n, 1), ka, wilson(ka, n)], "best_case_p": round(p, 4),
                        "verdict": "not shown (even the best case p > 0.05)" if p > 0.05 else "may be real (best case p <= 0.05); needs per-question results"})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "score-intervals.json").write_text(json.dumps({"scores": rows, "changes": changes}, indent=1), encoding="utf-8")
    print(f"{'where':22} {'score':32} {'%':>6} {'k/n':>7}  95 % interval")
    for r in rows:
        print(f"{r['where']:22} {r['score']:32} {r['pct']:6.1f} {r['k']:3d}/{r['n']:<3d}  {r['ci95'][0]:5.1f} - {r['ci95'][1]:5.1f}")
    print()
    for c in changes:
        print(f"{c['card']:18} set {c['set']:3} {c['change']:42} {c['before'][0]:5.1f} -> {c['after'][0]:5.1f} "
              f"({c['before'][1]} -> {c['after'][1]} of {c['n']})  best-case p {c['best_case_p']:.4f}  {c['verdict']}")


if __name__ == "__main__":
    main()
