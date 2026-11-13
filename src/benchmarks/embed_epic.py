"""EYKO-91 S3: embed frames of the 30 longest EPIC-KITCHENS-100 videos with MobileCLIP-S2. Run: task epic-vectors

Taha's choice (lead), 10 Nov 2026: S3 is first-person kitchen video, as decided on 8 Nov (D1). The
30 videos are 258 GB (largest 13.9 GB), more than the laptop's free disk, so no video is ever saved:
each one is streamed from EPIC's server over several parallel range requests (the server gives
about 0.1-0.5 MB/s per connection), decoded as it arrives, and one frame is taken every STEP
seconds. About 200 MB of memory holds the chunks in flight (48 of 4 MB). Only the vectors are kept, in
data/eyko91_epic/ (git-ignored, never committed; EPIC-KITCHENS is CC BY-NC 4.0).

The model is the app's (MobileCLIP-S2, datacompdr) run through open_clip in PyTorch. Its ONNX
export, which the phone runs, agrees with it to cosine >= 0.999 (export_clip.py checks that).

A video's rows are written only once the whole video is embedded, so a stopped run resumes at the
next video. Queries are 21 distinct narrations (seed 90) from EPIC's validation videos, none from
the 30 stored ones: real text, through the text encoder.
"""
import argparse
import csv
import http.client
import io
import json
import math
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
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
CHUNK = 4 << 20


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


def locate(video_id: str):
    """(url, size in bytes) of a video on EPIC's server."""
    for url in video_urls(video_id):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
                return url, int(r.headers["Content-Length"])
        except OSError:
            continue
    sys.exit(f"{video_id}: not found at {video_urls(video_id)}")


def get_range(url: str, start: int, end: int, tries: int = 20, wait=time.sleep) -> bytes:
    """Bytes start..end-1 of url, retrying broken or short reads."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end - 1}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if r.status == 206 and len(data) == end - start:
                return data
            err = f"got {len(data)} bytes, status {r.status}"
        except (OSError, http.client.HTTPException) as e:  # IncompleteRead is not an OSError
            err = e
        print(f"  bytes {start}-{end}: {err}, retrying", flush=True)
        wait(min(2 ** attempt, 60))
    raise OSError(f"could not read bytes {start}-{end} of {url}")


class RemoteFile(io.RawIOBase):
    """A seekable read-only file over HTTP range requests, fetching the next chunks in parallel.

    Only the chunks around the read position are kept, so a 14 GB video never touches the disk.
    Read-ahead starts at one chunk and grows with each read near the last one, so the far jumps a demuxer makes
    while opening a file (MP4 keeps its index at the end) do not queue chunks nobody reads.
    """

    def __init__(self, url: str, size: int, fetch=get_range, workers: int = 24, ahead: int = 48, chunk: int = CHUNK):
        self.url, self.size, self.fetch, self.ahead, self.chunk = url, size, fetch, ahead, chunk
        self.pool, self.jobs, self.pos, self.run = ThreadPoolExecutor(workers), {}, 0, 0
        self.got = self.waited = 0  # bytes downloaded, seconds spent waiting for them

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        pos = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence] + offset
        if abs(pos - self.pos) > 2 * self.chunk:  # a far jump; small ones (audio next to video) keep it
            self.run = 0
        self.pos = pos
        return self.pos

    def _job(self, i):
        if i not in self.jobs:
            start = i * self.chunk
            self.jobs[i] = self.pool.submit(self.fetch, self.url, start, min(start + self.chunk, self.size))
        return self.jobs[i]

    def readinto(self, buf):
        if self.pos >= self.size:
            return 0
        i, last = self.pos // self.chunk, (self.size - 1) // self.chunk
        ahead = min(self.ahead, self.run)
        for j in [j for j in self.jobs if j < i - 1 or j > i + max(ahead, 1)]:  # keep one chunk behind
            self.jobs.pop(j).cancel()
        for j in range(i, min(i + ahead, last) + 1):
            self._job(j)
        self.run += 1
        job = self.jobs[i]
        if not job.done():
            waited = time.perf_counter()
            job.result()
            self.waited += time.perf_counter() - waited
        data = job.result()
        if not getattr(job, "counted", False):
            job.counted = True
            self.got += len(data)
        off = self.pos - i * self.chunk
        n = min(len(buf), len(data) - off)
        buf[:n] = data[off:off + n]
        self.pos += n
        return n

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.jobs.clear()
        super().close()


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
    p.add_argument("--connections", type=int, default=24, help="parallel range requests (24 gave ~4.5 MB/s, 10 Nov)")
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
        url, size = locate(video_id)
        print(f"[{k}/{a.videos}] {video_id}: streaming {size / 1e9:.1f} GB", flush=True)
        began, vecs, times, batch = time.perf_counter(), [], [], []

        def flush():
            with torch.no_grad():
                vecs.append(torch.nn.functional.normalize(model.encode_image(torch.stack(batch)), dim=-1).numpy())
            batch.clear()

        remote = RemoteFile(url, size, workers=a.connections, ahead=2 * a.connections)
        with av.open(remote) as box:
            stream = box.streams.video[0]
            stream.thread_type = "AUTO"
            decoded = ((float(f.pts * stream.time_base), f) for f in box.decode(stream) if f.pts is not None)
            for t, frame in pick(decoded):
                batch.append(preprocess(frame.to_image()))
                times.append(t)
                if len(batch) == a.batch:
                    flush()
                if len(times) % 500 == 0:
                    s = time.perf_counter() - began
                    print(f"  {t / 60:5.1f} min of video, {len(times)} frames, {remote.got / s / 1e6:.2f} MB/s, "
                          f"{remote.waited / s:.0%} of the time waiting for the network", flush=True)
            if batch:
                flush()
        remote.close()
        with vec_path.open("ab") as vf, row_path.open("a") as rf:
            vf.write(np.concatenate(vecs).astype("<f4").tobytes())
            rf.write("".join(f"{video_id},{t:.3f}\n" for t in times))
        total += len(times)
        took = time.perf_counter() - began
        print(f"  {len(times)} frames in {took / 60:.0f} min ({size / took / 1e6:.2f} MB/s), {total} rows in all, "
              f"{(time.perf_counter() - start) / 3600:.1f} h so far", flush=True)
    print(f"written: {vec_path} ({total} x {DIM}), {queries_path} ({QUERIES} x {DIM})")


if __name__ == "__main__":
    main()
