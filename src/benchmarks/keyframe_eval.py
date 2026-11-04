"""Keyframe comparison, laptop side (card EYKO-45). Rules: docs/plans/keyframe-comparison-protocol.md

    task eval-keyframes -- <phone results json> [<more phone json> ...]

Scores each method's kept frames against the marked moments, at an equal budget: every method is
set to keep as many frames per clip as our method kept on the phone (the first json given).
"Ours" is not re-implemented here: its kept frames come from the phone run itself.
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np

CLIPS = Path("data/evals/keyframes/clips")
MOMENTS = Path("data/evals/keyframes/moments.csv")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 3.0  # the rate at which sharpness is measured for scoring
SMALL_SIDE = 320
MARGIN_S = 1.0  # a moment is widened by this much on each side
HELD_OUT_EVERY = 3  # by file-name order, every third clip is held out


def clip_info(path: Path) -> tuple[float, np.ndarray]:
    """Length in seconds, and the sharpness (variance of the Laplacian) of the frame at each 1/FPS step."""
    cap = cv2.VideoCapture(str(path))
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    sharpness = []
    for i in range(int(np.ceil(duration * FPS - 1e-6))):
        cap.set(cv2.CAP_PROP_POS_MSEC, i / FPS * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        k = max(1, round(max(gray.shape) / SMALL_SIDE))
        h, w = gray.shape[0] // k, gray.shape[1] // k
        small = cv2.resize(gray[: h * k, : w * k], (w, h), interpolation=cv2.INTER_AREA)
        sharpness.append(cv2.Laplacian(small, cv2.CV_64F).var())
    cap.release()
    return duration, np.array(sharpness)


def score(kept: list[float], moments: list[tuple[float, float]], sharpness: np.ndarray) -> dict:
    """Protocol section 4: a moment is hit by a sharp kept frame inside it (widened by MARGIN_S)."""
    limit = 0.5 * float(np.median(sharpness))

    def sharp(t: float) -> bool:
        return sharpness[min(len(sharpness) - 1, max(0, round(t * FPS)))] >= limit

    hit = sum(any(a - MARGIN_S <= t <= b + MARGIN_S and sharp(t) for t in kept) for a, b in moments)
    wasted = sum(not any(a - MARGIN_S <= t <= b + MARGIN_S for a, b in moments) for t in kept)
    return {"kept": len(kept), "hit": hit, "moments": len(moments), "wasted": wasted}


# ── the methods: each returns the times (seconds) of the frames it keeps ─────────────────────


def uniform(duration: float, n: int) -> list[float]:
    return [(i + 0.5) * duration / n for i in range(n)]


def iframes(path: Path) -> list[float]:
    """The frames the file stores in full. Cannot be set to a budget."""
    err = subprocess.run(
        [FFMPEG, "-skip_frame", "nokey", "-i", str(path), "-vf", "showinfo", "-an", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stderr
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", err)]


def ffmpeg_scene(path: Path, n: int) -> list[float]:
    """ffmpeg's scene filter. Keeping the n frames with the highest scene score is the same as
    choosing the threshold that lets n frames through."""
    out = subprocess.run(
        [FFMPEG, "-i", str(path), "-vf", "select='gte(scene,0)',metadata=print:file=-", "-an", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    times = [float(t) for t in re.findall(r"pts_time:([\d.]+)", out)]
    scores = [float(s) for s in re.findall(r"lavfi\.scene_score=([\d.]+)", out)]
    best = sorted(range(len(scores)), key=lambda i: -scores[i])[:n]
    return sorted(times[i] for i in best)


def pyscenedetect(path: Path, n: int, adaptive: bool) -> list[float]:
    """PySceneDetect: find cuts, keep the middle frame of each scene. The threshold is searched
    so that the number of scenes is as close to n as it can get."""
    from scenedetect import AdaptiveDetector, ContentDetector, detect

    def scenes(threshold: float):
        detector = AdaptiveDetector(adaptive_threshold=threshold, min_scene_len=5) if adaptive else ContentDetector(threshold=threshold, min_scene_len=5)
        return detect(str(path), detector, start_in_scene=True)

    low, high = (0.2, 12.0) if adaptive else (1.0, 80.0)
    best = scenes(low)
    for _ in range(12):  # more scenes at a lower threshold: bisect towards n
        mid = (low + high) / 2
        found = scenes(mid)
        if abs(len(found) - n) < abs(len(best) - n):
            best = found
        if len(found) > n:
            low = mid
        elif len(found) < n:
            high = mid
        else:
            break
    return [(a.seconds + b.seconds) / 2 for a, b in best]


# ── running it ────────────────────────────────────────────────────────────────────────────────


def main(phone_files: list[str]) -> None:
    clips = sorted(CLIPS.glob("*.mp4"))
    marks: dict[str, list[tuple[float, float]]] = {c.name: [] for c in clips}
    for row in csv.DictReader(MOMENTS.open(encoding="utf-8")):
        marks[row["clip"]].append((float(row["start_s"]), float(row["end_s"])))

    phones = [json.loads(Path(f).read_text(encoding="utf-8")) for f in phone_files]
    ours = [{c["clip"]: c["ours"][0]["kept_times"] for c in phone["clips"]} for phone in phones]  # clipN.mp4 = Nth by name

    rows = []  # (group, clip number, method, score)
    for number, clip in enumerate(clips, start=1):
        duration, sharpness = clip_info(clip)
        group = "held out" if number % HELD_OUT_EVERY == 0 else "tuning"
        n = len(ours[0][f"clip{number}.mp4"])
        methods = {f"ours ({phone['device']})": kept[f"clip{number}.mp4"] for phone, kept in zip(phones, ours)}
        methods |= {
            "B0 uniform": uniform(duration, n),
            "B1 codec keyframes (no budget)": iframes(clip),
            "B2 ffmpeg scene filter": ffmpeg_scene(clip, n),
            "B3 PySceneDetect content": pyscenedetect(clip, n, adaptive=False),
            "B3 PySceneDetect adaptive": pyscenedetect(clip, n, adaptive=True),
        }
        for name, kept in methods.items():
            rows.append((group, number, name, score(kept, marks[clip.name], sharpness) | {"minutes": duration / 60}))
        print(f"clip {number} ({duration:.1f} s, {len(marks[clip.name])} moments, budget {n}) done", file=sys.stderr)

    names = list(dict.fromkeys(r[2] for r in rows))
    for group in ("tuning", "held out", "all"):
        chosen = [r for r in rows if group == "all" or r[0] == group]
        print(f"\n### {group} clips ({', '.join(str(n) for n in sorted({r[1] for r in chosen}))})\n")
        print("| Method | Frames kept | Kept per minute | Moments hit | Moment recall | Wasted frames |")
        print("|---|---|---|---|---|---|")
        for name in names:
            s = [r[3] for r in chosen if r[2] == name]
            kept, hit, total = sum(x["kept"] for x in s), sum(x["hit"] for x in s), sum(x["moments"] for x in s)
            wasted, minutes = sum(x["wasted"] for x in s), sum(x["minutes"] for x in s)
            print(f"| {name} | {kept} | {kept / minutes:.1f} | {hit} of {total} | {hit / total:.0%} | {wasted} of {kept} ({wasted / max(kept, 1):.0%}) |")
    print("\n### per clip (moments hit / frames kept)\n")
    print("| Method | " + " | ".join(f"clip {n}" for n in range(1, len(clips) + 1)) + " |")
    print("|---|" + "---|" * len(clips))
    for name in names:
        cells = [next(f"{r[3]['hit']}/{r[3]['moments']} with {r[3]['kept']}" for r in rows if r[1] == n and r[2] == name) for n in range(1, len(clips) + 1)]
        print(f"| {name} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main(sys.argv[1:])
