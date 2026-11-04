"""Motion-paced keyframes: a laptop trial of a cheaper keyframe step (card EYKO-45).

    task eval-keyframes-motion -- <clips folder> <moments csv> <cache folder> <video ids, comma separated> [<budget>:<max gap> ...]

The method uses no image model. Frames come at 3 a second. A stretch of video ends when the
summed frame-to-frame change passes `budget`, or after `max gap` frames; the sharpest frame of
each stretch is kept. So a still camera gives few frames and a moving one gives more.
Each setting is compared with evenly spaced frames at the same total number of frames.
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

import keyframe_eval as ev
import keyframe_tune as tune

SETTINGS = ((200.0, 12), (300.0, 18))  # chosen on the tuning videos, see docs/results


def features(clip: Path, cache: Path) -> dict:
    """Per frame at 3 a second: change since the frame before, and sharpness. Kept on disk."""
    file = cache / f"{clip.stem.replace(' ', '_')}_motion.npz"
    if file.exists():
        return dict(np.load(file))
    grays = [tune.small_gray(f) for f in tune.frames_of(clip)]
    duration, sharpness = ev.clip_info(clip)
    out = dict(
        motion=np.array([0.0] + [float(cv2.absdiff(a, b).mean()) for a, b in zip(grays, grays[1:])]),
        blur=np.array([cv2.Laplacian(g, cv2.CV_64F).var() for g in grays]),
        duration=np.array(duration), sharpness=sharpness,
    )
    np.savez_compressed(file, **out)
    return out


def motion_paced(motion: np.ndarray, blur: np.ndarray, budget: float, max_gap: int) -> list[int]:
    kept, start, moved = [], 0, 0.0
    for i in range(len(motion)):
        moved += motion[i]
        if moved >= budget or i - start + 1 >= max_gap or i == len(motion) - 1:
            kept.append(start + int(np.argmax(blur[start : i + 1])))
            start, moved = i + 1, 0.0
    return kept


def spaced(count: int, n: int, blur: np.ndarray | None = None) -> list[int]:
    """n evenly spaced frames out of count; with blur given, the sharpest frame of each slot."""
    edges = [round(i * count / n) for i in range(n + 1)]
    if blur is None:
        return [min(count - 1, (a + b) // 2) for a, b in zip(edges, edges[1:])]
    return [a + int(np.argmax(blur[a : max(b, a + 1)])) for a, b in zip(edges, edges[1:])]


def main(clips_dir: str, moments_csv: str, cache_dir: str, ids: str, *settings: str) -> None:
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    chosen = [tuple(float(x) for x in s.split(":")) for s in settings] or SETTINGS
    marks: dict[str, list] = {}
    for row in csv.DictReader(open(moments_csv, encoding="utf-8")):
        marks.setdefault(Path(row["clip"]).stem, []).append((float(row["start_s"]), float(row["end_s"])))
    data = {v: features(Path(clips_dir) / f"{v}.mp4", cache) for v in ids.split(",")}
    frames = sum(len(f["motion"]) for f in data.values())
    moments = sum(len(marks.get(v, [])) for v in data)
    minutes = sum(float(f["duration"]) for f in data.values()) / 60

    def total(pick) -> tuple[int, int]:
        kept = hit = 0
        for v, f in data.items():
            s = ev.score([i / tune.FPS for i in pick(f)], marks.get(v, []), f["sharpness"])
            kept, hit = kept + s["kept"], hit + s["hit"]
        return kept, hit

    print(f"{len(data)} videos, {minutes:.1f} min, {moments} moments\n")
    print("| Budget : max gap | Frames kept (per minute) | Motion-paced | Evenly spaced | Evenly spaced, sharpest of each slot |")
    print("|---|---|---|---|---|")
    for budget, gap in chosen:
        kept, hit = total(lambda f: motion_paced(f["motion"], f["blur"], budget, int(gap)))
        share = kept / frames  # the same share of every video's frames: one rate, blind to the content
        even = total(lambda f: spaced(len(f["motion"]), max(1, round(len(f["motion"]) * share))))
        even_sharp = total(lambda f: spaced(len(f["motion"]), max(1, round(len(f["motion"]) * share)), f["blur"]))
        print(f"| {budget:g} : {int(gap)} | {kept} ({kept / minutes:.0f}) | {hit} | {even[1]} with {even[0]} | {even_sharp[1]} with {even_sharp[0]} |")


if __name__ == "__main__":
    main(*sys.argv[1:])
