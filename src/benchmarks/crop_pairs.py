"""Choose the "same object" threshold for card EYKO-15 from measured pairs. Run:

    task crop-pairs -- <object crops json from the phone> <identity csv>

The phone's ObjectCropBenchmarkTest saves every detected object's own crop with its MobileCLIP
vector. The identity csv says which crops show the same physical object (crops left out of it
were unclear). Pairs are only made between crops with the same detector name, because the stage
only ever compares sightings with the same name, and never from the same frame.
  same       two crops of one object, from different frames
  different  two crops of two different objects
The threshold printed is the one with the fewest wrong calls over both lists (ties: the middle
of the tied range). Both lists of numbers are printed so the choice can be checked.
"""
import csv
import json
import sys
from itertools import combinations

import numpy as np


def main() -> None:
    crops = {c["crop"]: c for c in json.load(open(sys.argv[1], encoding="utf-8"))["crops"]}
    objects = {r["crop"]: r["object"] for r in csv.DictReader(open(sys.argv[2], encoding="utf-8"))}
    same, different = [], []
    for a, b in combinations(sorted(objects), 2):
        ca, cb = crops[a], crops[b]
        if ca["label"] != cb["label"] or (ca["clip"], ca["frame_no"]) == (cb["clip"], cb["frame_no"]):
            continue
        cosine = float(np.dot(ca["vector"], cb["vector"]))
        (same if objects[a] == objects[b] else different).append((cosine, ca["label"], objects[a], objects[b]))
    same.sort(); different.sort()
    print(f"{len(objects)} crops of {len(set(objects.values()))} objects; {len(same)} same-object pairs, {len(different)} different-object pairs")
    for name, pairs in (("same", same), ("different", different)):
        values = [p[0] for p in pairs]
        print(f"{name:9} lowest {values[0]:.3f}, a quarter below {np.percentile(values, 25):.3f}, middle {np.median(values):.3f}, "
              f"three quarters below {np.percentile(values, 75):.3f}, highest {values[-1]:.3f}")
        print("  all:", " ".join(f"{v:.2f}" for v in values))

    candidates = [round(0.50 + 0.01 * i, 2) for i in range(50)]
    wrong = {t: sum(c < t for c, *_ in same) + sum(c >= t for c, *_ in different) for t in candidates}
    best = min(wrong.values())
    tied = [t for t in candidates if wrong[t] == best]
    chosen = tied[len(tied) // 2]
    print(f"fewest wrong calls: {best} of {len(same) + len(different)} for thresholds {tied[0]} to {tied[-1]}; chosen {chosen}")
    for t in (0.70, 0.75, 0.80, 0.85, 0.90, chosen):
        print(f"  at {t:.2f}: {sum(c < t for c, *_ in same)} of {len(same)} same pairs called different, "
              f"{sum(c >= t for c, *_ in different)} of {len(different)} different pairs called same")
    print("same pairs below the chosen value:", [(round(c, 2), label, a) for c, label, a, _ in same if c < chosen])
    print("different pairs at or above it:", [(round(c, 2), label, a, b) for c, label, a, b in different if c >= chosen])
    by_label = {}
    for c, label, *_ in same: by_label.setdefault(label, [0, 0])[0] += 1
    for c, label, *_ in different: by_label.setdefault(label, [0, 0])[1] += 1
    print("pairs by name (same, different):", by_label)


if __name__ == "__main__":
    main()
