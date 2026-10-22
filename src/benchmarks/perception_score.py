"""Score the phone's perception run (card EYKO-9) against hand labels. Run: task eval-perception -- <bench.json> <labels.csv>

The rules, fixed before the phone's answers were read:
  main object  the frame's most prominent thing the detector can know (one of its 80 classes).
               "person": right when at least one person is counted. Another class: right when it
               is among the listed objects. "none": right when nothing at all is reported.
  other object the most prominent thing that is not a person; right when it is among the objects.
               Frames labelled "none" are left out of this row.
  place        right when the phrase equals the label; "none" (the real place is not one of the
               phrases) is right only when no place is given.
"""
import csv
import json
import statistics
import sys
from collections import Counter


def main() -> None:
    bench = json.load(open(sys.argv[1], encoding="utf-8"))
    labels = {row["frame"]: row for row in csv.DictReader(open(sys.argv[2], encoding="utf-8"))}
    frames = bench["frames"]
    assert {f["frame"][:-4] for f in frames} == set(labels), "frames and labels differ"

    right = Counter()
    asked = Counter()
    misses = []
    for f in frames:
        label = labels[f["frame"][:-4]]
        found = [o["label"] for o in f["objects"]]
        main = label["main_object"]
        checks = {
            "main object": f["people"] > 0 if main == "person" else (not found and f["people"] == 0) if main == "none" else main in found,
            "place": f["place"] == (None if label["place"] == "none" else label["place"]),
        }
        if label["other_object"] != "none":
            checks["other object"] = label["other_object"] in found
        if main not in ("person", "none"):
            checks["main object, not a person"] = main in found
        if label["place"] != "none":
            checks["place, when it is one of the phrases"] = f["place"] == label["place"]
        for name, ok in checks.items():
            asked[name] += 1
            right[name] += ok
        wrong = [name for name in ("main object", "other object", "place") if checks.get(name) is False]
        if wrong:
            misses.append((f["frame"][:-4], wrong, f["people"], found, f["place"]))

    print(f"{bench.get('detector', 'yolox_nano.onnx')} on {bench['device']}, Android {bench['android']}, {bench['build']} build; {len(frames)} frames; "
          f"detector confidence {bench['detector_conf']}, phrase minimum {bench['prompt_min']}")
    for name in ("main object", "main object, not a person", "other object", "place", "place, when it is one of the phrases"):
        if asked[name]:
            print(f"  {name:38} {right[name]:2} of {asked[name]:2}  ({100 * right[name] / asked[name]:.0f} %)")
    for key, title in (("full_ms", "detector + image model + phrases"), ("with_saved_vector_ms", "detector + phrases, saved image vector")):
        times = sorted(f[key] for f in frames)
        print(f"  {title:38} median {statistics.median(times):.0f} ms, worst {times[-1]:.0f} ms per frame")
    print(f"  peak memory: native {bench['peak_native_heap_mb']} MB, java {bench['peak_java_heap_mb']} MB")
    print("  places given:", dict(Counter(str(f["place"]) for f in frames)))
    print("  actions given:", dict(Counter(str(f["action"]) for f in frames)))
    print("  things listed:", dict(Counter(o["label"] for f in frames for o in f["objects"])))
    print("misses (frame, what, people counted, things listed, place given):")
    for miss in misses:
        print("  ", *miss)


if __name__ == "__main__":
    main()
