"""EYKO-91 S3: embed frames of the 30 longest EPIC-KITCHENS-100 videos with MobileCLIP-S2. Run: task epic-vectors

Taha's choice (lead), 10 Nov 2026: S3 is first-person kitchen video, as decided on 8 Nov (D1). The 30
videos are about 250 GB, too much for Taha's connection, so this runs on a helper machine
(EYKO-113). One video is fetched at a time into data/eyko91_epic/tmp/, one frame is taken every
STEP seconds, the frames are embedded, and the video is deleted: about 15 GB of free disk is enough.
Only the vectors are kept, in data/eyko91_epic/ (git-ignored, never committed; EPIC-KITCHENS is
CC BY-NC 4.0).

The model is the app's (MobileCLIP-S2, datacompdr) run through open_clip in PyTorch. Its ONNX
export, which the phone runs, agrees with it to cosine >= 0.999 (export_clip.py checks that).

A video's rows are written only once the whole video is embedded, so a stopped run resumes at the
next video, and a half-fetched video resumes its download. Queries are 21 distinct narrations
(seed 90) from EPIC's validation videos, none from the 30 stored ones: real text, through the text
encoder.
"""
import argparse
import csv
import io
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/eyko91_epic"
MODEL, PRETRAINED, DIM = "MobileCLIP-S2", "datacompdr", 512
# 0.75 s (the 8 Nov plan) gives 99,774 frames, 226 short of the 100k size; 0.745 s gives 100,441.
STEP = 0.745
VIDEOS = ("P01_109 P01_18 P01_09 P23_102 P10_04 P35_104 P30_05 P35_108 P30_107 P13_08 P27_103 P20_04 "
          "P23_04 P25_107 P33_105 P02_09 P22_07 P35_105 P01_105 P23_103 P29_03 P04_05 P07_10 P12_101 "
          "P22_109 P24_09 P12_04 P04_105 P06_101 P12_02").split()  # the 30 longest, EPIC_100_video_info.csv
ANNOTATIONS = "https://raw.githubusercontent.com/epic-kitchens/epic-kitchens-100-annotations/master/"
EPIC55 = "https://data.bris.ac.uk/datasets/3h91syskeag572hl6tvuovwv4d/videos/{split}/{p}/{v}.MP4"
EPIC100 = "https://data.bris.ac.uk/datasets/2g1n6qdydwa9u22shpxqzp0t8m/{p}/videos/{v}.MP4"
QUERIES = 21  # 1 warm-up + 20 timed, as the benchmark uses


def video_urls(video_id: str) -> list:
    """Where a video lives: the EPIC-100 extension (P01_101 and up) or EPIC-55 (train or test)."""
    p = video_id.split("_")[0]
    if int(video_id.split("_")[1]) >= 100:
        return [EPIC100.format(p=p, v=video_id)]
    return [EPIC55.format(split=s, p=p, v=video_id) for s in ("train", "test")]


def pick(frames, step: float = STEP):
    """From (seconds, frame) in time order, yield the first frame at or after 0, step, 2*step, ..."""
    target = 0.0
    for t, frame in frames:
        if t >= target - 1e-9:
            yield t, frame
            target = (math.floor(t / step + 1e-9) + 1) * step


def fetch(video_id: str) -> Path:
    """Download one video into OUT/tmp (resuming a partial file) and return its path."""
    tmp = OUT / "tmp"
    tmp.mkdir(exist_ok=True)
    path = tmp / f"{video_id}.MP4"
    for url in video_urls(video_id):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
                size = int(r.headers["Content-Length"])
        except OSError:
            continue
        for attempt in range(20):
            have = path.stat().st_size if path.exists() else 0
            if have == size:
                return path
            try:
                req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if 0 < have < size else {})
                with urllib.request.urlopen(req, timeout=120) as r, path.open("ab" if r.status == 206 else "wb") as f:
                    while chunk := r.read(1 << 22):
                        f.write(chunk)
            except OSError as e:
                print(f"  {video_id}: {e}, retrying", flush=True)
                time.sleep(min(2 ** attempt, 60))
        sys.exit(f"{video_id}: could not finish the download from {url}")
    sys.exit(f"{video_id}: not found at {video_urls(video_id)}")


def narrations() -> list:
    """21 distinct validation narrations (seed 90), none from the stored videos."""
    with urllib.request.urlopen(ANNOTATIONS + "EPIC_100_validation.csv", timeout=120) as r:
        rows = list(csv.DictReader(io.TextIOWrapper(r, encoding="utf-8")))
    texts = sorted({row["narration"].strip() for row in rows if row["video_id"] not in VIDEOS})
    picked = np.random.default_rng(90).choice(len(texts), QUERIES, replace=False)
    return [texts[i] for i in picked]


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--videos", type=int, default=len(VIDEOS), help="embed only the first N videos (a test run)")
    p.add_argument("--batch", type=int, default=64)
    a = p.parse_args()

    import av
    import open_clip
    import torch
    from timm.utils import reparameterize_model

    OUT.mkdir(parents=True, exist_ok=True)
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED, device="cpu")
    model = reparameterize_model(model.eval()).eval()
    tokenizer = open_clip.get_tokenizer(MODEL)

    queries_path = OUT / "queries_512.f32"
    if not queries_path.exists():
        texts = narrations()
        with torch.no_grad():
            q = torch.nn.functional.normalize(model.encode_text(tokenizer(texts)), dim=-1).numpy()
        q.astype("<f4").tofile(queries_path)
        (OUT / "queries.json").write_text(json.dumps(texts, indent=1) + "\n", encoding="utf-8")
        print("queries:", *texts, sep="\n  ")

    vec_path, row_path = OUT / "images_512.f32", OUT / "frames.csv"  # frames.csv: video_id,seconds per row
    rows = row_path.read_text().splitlines() if row_path.exists() else []
    if (vec_path.stat().st_size if vec_path.exists() else 0) != len(rows) * DIM * 4:
        sys.exit(f"{vec_path} and {row_path} disagree; delete both to start again")
    done, total = {r.split(",")[0] for r in rows}, len(rows)
    start = time.perf_counter()
    for k, video_id in enumerate(VIDEOS[: a.videos], 1):
        if video_id in done:
            continue
        print(f"[{k}/{a.videos}] {video_id}: fetching", flush=True)
        path = fetch(video_id)
        vecs, times, batch = [], [], []

        def flush():
            with torch.no_grad():
                vecs.append(torch.nn.functional.normalize(model.encode_image(torch.stack(batch)), dim=-1).numpy())
            batch.clear()

        with av.open(str(path)) as box:
            stream = box.streams.video[0]
            stream.thread_type = "AUTO"
            decoded = ((float(f.pts * stream.time_base), f) for f in box.decode(stream) if f.pts is not None)
            for t, frame in pick(decoded):
                batch.append(preprocess(frame.to_image()))
                times.append(t)
                if len(batch) == a.batch:
                    flush()
            if batch:
                flush()
        with vec_path.open("ab") as vf, row_path.open("a") as rf:
            vf.write(np.concatenate(vecs).astype("<f4").tobytes())
            rf.write("".join(f"{video_id},{t:.3f}\n" for t in times))
        path.unlink()
        total += len(times)
        print(f"  {len(times)} frames, {total} rows in all, {(time.perf_counter() - start) / 3600:.1f} h so far", flush=True)
    print(f"written: {vec_path} ({total} x {DIM}), {queries_path} ({QUERIES} x {DIM})")


if __name__ == "__main__":
    main()
