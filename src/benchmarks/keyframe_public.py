"""Keyframe comparison on an outside dataset with other people's marks (card EYKO-45).

    task eval-keyframes-public -- <clips folder> <moments csv> <mobileclip onnx> <cache folder> [<groups csv>]

Same scoring as keyframe_eval.py. "Ours" is the laptop copy of the phone's layers at the phone's
own thresholds (keyframe_tune.py), so nothing here is tuned on these clips. The optional groups
csv has columns video_id, group and splits the tables.
"""
import csv
import sys
from pathlib import Path

import keyframe_eval as ev
import keyframe_tune as tune

FIXED_RATES = (0.5, 1.0)  # uniform at one rate for every clip, frames per second


def main(clips_dir: str, moments_csv: str, model: str, cache_dir: str, groups_csv: str = "") -> None:
    import onnxruntime as ort

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    session = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    clips = sorted(Path(clips_dir).glob("*.mp4"))
    marks = {c.name: [] for c in clips}
    for row in csv.DictReader(open(moments_csv, encoding="utf-8")):
        marks[row["clip"]].append((float(row["start_s"]), float(row["end_s"])))
    group_of = {r["video_id"]: r["group"] for r in csv.DictReader(open(groups_csv, encoding="utf-8"))} if groups_csv else {}

    rows = []  # (group, clip, method, score)
    for clip in clips:
        duration, sharpness = ev.clip_info(clip)
        kept, calls = tune.ours(tune.features(clip, session, cache), tune.PHONE)
        n = max(1, len(kept))
        methods = {
            "ours (laptop copy, phone thresholds)": [i / tune.FPS for i in kept],
            "B0 uniform, same count": ev.uniform(duration, n),
            "B1 codec keyframes (no budget)": ev.iframes(clip),
            "B2 ffmpeg scene filter": ev.ffmpeg_scene(clip, n),
            "B3 PySceneDetect content": ev.pyscenedetect(clip, n, adaptive=False),
        } | {f"B0 uniform, {r} a second": ev.uniform(duration, max(1, round(duration * r))) for r in FIXED_RATES}
        for name, times in methods.items():
            rows.append((group_of.get(clip.stem, "all"), clip.stem, name, ev.score(times, marks[clip.name], sharpness) | {"minutes": duration / 60}))
        print(f"{clip.stem}: {duration:.1f} s, {len(marks[clip.name])} moments, ours kept {n}, model ran {calls} times", file=sys.stderr)

    names = list(dict.fromkeys(r[2] for r in rows))
    for group in [*dict.fromkeys(r[0] for r in rows), "all"]:
        chosen = [r for r in rows if group == "all" or r[0] == group]
        print(f"\n### {group} ({', '.join(sorted({r[1] for r in chosen}))})\n")
        print("| Method | Frames kept | Kept per minute | Moments hit | Moment recall | Wasted frames |")
        print("|---|---|---|---|---|---|")
        for name in names:
            s = [r[3] for r in chosen if r[2] == name]
            kept, hit, total = sum(x["kept"] for x in s), sum(x["hit"] for x in s), sum(x["moments"] for x in s)
            wasted, minutes = sum(x["wasted"] for x in s), sum(x["minutes"] for x in s)
            print(f"| {name} | {kept} | {kept / minutes:.1f} | {hit} of {total} | {hit / total:.0%} | {wasted} of {kept} ({wasted / max(kept, 1):.0%}) |")


if __name__ == "__main__":
    main(*sys.argv[1:])
