"""Katna (B4) in the keyframe comparison (card EYKO-131). Rules: docs/plans/keyframe-comparison-protocol.md

    uv run --no-project --python 3.10 --with katna --with imageio-ffmpeg python src/benchmarks/keyframe_katna.py \
        <clips folder> <moments csv> <phone results json>

Katna keeps the number of frames it is asked for, so it gets the same number per clip as ours kept on
the phone (equal budget, protocol section 4). Katna hands back pictures without times, so each picture is
matched to the decoded frame it came from (smallest difference on a 64 x 36 grey copy). Clips above 720 p
are given to Katna as the same 360 p copy PySceneDetect uses; scoring is on the original, as for every method.
Katna is not added to pyproject.toml: it runs in a one-off environment.
"""
import csv
import importlib.metadata
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import keyframe_eval as ev  # noqa: E402

THUMB = (64, 36)


def thumb(frame: np.ndarray) -> np.ndarray:
    return cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), THUMB, interpolation=cv2.INTER_AREA).astype(np.float32)


def all_thumbs(path: Path) -> tuple[np.ndarray, float]:
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        out.append(thumb(frame))
    cap.release()
    return np.stack(out), fps


def katna_times(path: Path, n: int) -> tuple[list[float], float]:
    from Katna.video import Video
    from Katna.writer import Writer

    class Keep(Writer):
        frames: list = []

        def write(self, filepath, data):
            Keep.frames = list(data)

    start = time.perf_counter()
    Video().extract_video_keyframes(no_of_frames=n, file_path=str(path), writer=Keep())
    seconds = time.perf_counter() - start
    thumbs, fps = all_thumbs(path)
    times = sorted(float(np.argmin(((thumbs - thumb(f)) ** 2).mean(axis=(1, 2)))) / fps for f in Keep.frames)
    return times, seconds


def main(clips_dir: str, moments_csv: str, phone_json: str) -> None:
    clips = sorted(Path(clips_dir).glob("*.mp4"))
    marks = {c.name: [] for c in clips}
    for row in csv.DictReader(open(moments_csv, encoding="utf-8")):
        marks[row["clip"]].append((float(row["start_s"]), float(row["end_s"])))
    ours = {c["clip"]: c["ours"][0]["kept_times"] for c in json.loads(Path(phone_json).read_text(encoding="utf-8"))["clips"]}
    print(f"Katna {importlib.metadata.version('katna')}\n")
    print("| Clip | Frames (= ours) | Katna kept | Katna hit | Ours hit | Moments | Katna wasted | Katna s per video minute |")
    print("|---|---|---|---|---|---|---|---|")
    total = dict(n=0, kept=0, hit=0, ours=0, moments=0, wasted=0, seconds=0.0, minutes=0.0)
    for number, clip in enumerate(clips, start=1):
        duration, sharpness = ev.clip_info(clip)
        n = len(ours[f"clip{number}.mp4"])
        times, seconds = katna_times(ev.small_copy(clip), max(1, n))
        k = ev.score(times, marks[clip.name], sharpness)
        o = ev.score(ours[f"clip{number}.mp4"], marks[clip.name], sharpness)
        print(f"| {clip.name} | {n} | {k['kept']} | {k['hit']} | {o['hit']} | {k['moments']} | {k['wasted']} | {seconds / (duration / 60):.1f} |", flush=True)
        for key, value in dict(n=n, kept=k["kept"], hit=k["hit"], ours=o["hit"], moments=k["moments"], wasted=k["wasted"], seconds=seconds, minutes=duration / 60).items():
            total[key] += value
    t = total
    print(f"| **all** | {t['n']} | {t['kept']} | **{t['hit']}** | {t['ours']} | {t['moments']} | {t['wasted']} of {t['kept']} | {t['seconds'] / t['minutes']:.1f} |")


if __name__ == "__main__":
    main(*sys.argv[1:])
