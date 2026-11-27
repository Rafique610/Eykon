"""Drop repeats against the whole video or only the last W seconds? (card EYKO-132)

    uv run --with scenedetect python src/benchmarks/keyframe_window.py <mobileclip image onnx> <clips folder> <moments csv> \
        [<phone results json to check the copy against>] [<cache folder>]

A laptop copy of today's phone layers: the cheap filters with the 3-second slot rule (FrameFilters.pickSlot),
then the hash and MobileCLIP repeat layers (VideoDedup), at the phone's cut-offs. keyframe_tune.py's copy
predates the slot rule, so this one adds it. With a phone json it first prints how many of the phone's kept
frames the copy keeps too. Then it scores the whole-video rule and W = 5, 10, 30, 60 s with the same scorer.
The decision uses W = 30 s only (docs/results/2026-11-27-dedup-recent-or-whole.md); nothing is tuned here.
"""
import csv
import json
import math
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent))
import keyframe_eval as ev  # noqa: E402
import keyframe_tune as tune  # noqa: E402

PHONE = tune.PHONE
SLOT = 9  # FrameFilters.SLOT_FRAMES
WINDOWS = (math.inf, 5.0, 10.0, 30.0, 60.0)


def filter_with_slots(f: dict) -> list[int]:
    """FrameFilters.pickSlot over slots of 9: the sharpest usable frame of each slot, if it passes check()."""
    kept, prev = [], None
    n = len(f["blur"])
    for start in range(0, n, SLOT):
        usable = [i for i in range(start, min(n, start + SLOT)) if PHONE["dark"] <= f["brightness"][i] <= PHONE["bright"]]
        if not usable:
            continue
        i = max(usable, key=lambda j: f["blur"][j])
        if f["blur"][i] < PHONE["blur"]:
            continue
        if prev is not None and cv2.absdiff(f["grays"][prev], f["grays"][i]).mean() < PHONE["diff"] and \
                cv2.compareHist(tune.ev_hist(f["grays"][prev]), tune.ev_hist(f["grays"][i]), cv2.HISTCMP_BHATTACHARYYA) < PHONE["hist"]:
            continue
        kept.append(i)
        prev = i
    return kept


def dedup(f: dict, candidates: list[int], window_s: float) -> tuple[list[int], int]:
    """VideoDedup: hash, then MobileCLIP, each against unique frames kept in the last window_s seconds."""
    unique, calls = [], 0
    for i in candidates:
        recent = [u for u in unique if (i - u) / tune.FPS <= window_s]
        if any(bin(int(f["hashes"][i]) ^ int(f["hashes"][u])).count("1") <= PHONE["hash_max"] for u in recent):
            continue
        calls += 1
        if recent and max(float(f["vectors"][i] @ f["vectors"][u]) for u in recent) >= PHONE["cos_min"]:
            continue
        unique.append(i)
    return unique, calls


def main(model: str, clips_dir: str, moments_csv: str, phone_json: str = "", cache_dir: str = "D:/eykon-cache/bench/window-cache") -> None:
    import onnxruntime as ort

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    session = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    clips = sorted(Path(clips_dir).glob("*.mp4"))
    marks = {c.name: [] for c in clips}
    for row in csv.DictReader(open(moments_csv, encoding="utf-8")):
        marks[row["clip"]].append((float(row["start_s"]), float(row["end_s"])))
    phone = {c["clip"]: c["ours"][0]["kept_times"] for c in json.loads(Path(phone_json).read_text(encoding="utf-8"))["clips"]} if phone_json else {}

    rows = {w: dict(kept=0, hit=0, wasted=0, calls=0) for w in WINDOWS}
    moments = 0
    if phone:
        print("## Does the laptop copy keep the phone's frames? (whole video, phone cut-offs)\n")
        print("| Clip | Phone kept | Copy kept | Same second (within 0.05 s) |")
        print("|---|---|---|---|")
    per_clip, whole = [], []  # whole: the copy's whole-video frames, in the phone json shape (Katna's budget, EYKO-131)
    for number, clip in enumerate(clips, start=1):
        duration, sharpness = ev.clip_info(clip)
        f = tune.features(clip, session, cache)
        candidates = filter_with_slots(f)
        moments += len(marks[clip.name])
        cells = []
        for w in WINDOWS:
            idx, calls = dedup(f, candidates, w)
            times = [i / tune.FPS for i in idx]
            s = ev.score(times, marks[clip.name], sharpness)
            for k in ("kept", "hit", "wasted"):
                rows[w][k] += s[k]
            rows[w]["calls"] += calls
            cells.append(f"{s['hit']}/{s['moments']} with {s['kept']}")
            if w == math.inf and phone:
                theirs = phone.get(f"clip{number}.mp4", [])
                same = sum(any(abs(t - p) <= 0.05 for p in theirs) for t in times)
                print(f"| {clip.name} | {len(theirs)} | {len(times)} | {same} |", flush=True)
        per_clip.append((clip.name, cells))
        whole.append({"clip": f"clip{number}.mp4", "ours": [{"kept_times": [i / tune.FPS for i in dedup(f, candidates, math.inf)[0]]}]})
        print(f"{clip.name} done", file=sys.stderr, flush=True)

    (cache / f"ours-laptop-{Path(clips_dir).parent.name}.json").write_text(json.dumps({"device": "laptop copy", "clips": whole}), encoding="utf-8")
    name = {math.inf: "whole video (the app today)"} | {w: f"last {w:.0f} s only" for w in WINDOWS[1:]}
    print(f"\n## Repeats against the whole video or the last W seconds ({len(clips)} clips, {moments} moments)\n")
    print("| Rule | Frames kept | Moments hit | Recall | Kept frames outside every moment | MobileCLIP runs |")
    print("|---|---|---|---|---|---|")
    for w in WINDOWS:
        r = rows[w]
        print(f"| {name[w]} | {r['kept']} | {r['hit']} of {moments} | {r['hit'] / max(moments, 1):.1%} | {r['wasted']} | {r['calls']} |")
    print("\n### per clip (moments hit / frames kept)\n")
    print("| Clip | " + " | ".join(name[w] for w in WINDOWS) + " |")
    print("|---|" + "---|" * len(WINDOWS))
    for clip_name, cells in per_clip:
        print(f"| {clip_name} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main(*sys.argv[1:])
