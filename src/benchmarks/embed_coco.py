"""EYKO-91 S3: embed COCO train2017 photos and val2017 captions with MobileCLIP-S2. Run: task coco-vectors

Owner's choice, 8 Nov 2026: the EPIC-KITCHENS slice is ~250 GB and the connection is slow, so S3
uses the plan's fallback. Each photo is fetched into memory, embedded, and dropped: no image is
ever written to disk. Only the vectors are kept, in data/eyko91_coco/ (git-ignored, never committed;
COCO images are Flickr photos under their own licences, the captions are CC BY 4.0).

The model is the app's (MobileCLIP-S2, datacompdr) run through open_clip in PyTorch. Its ONNX
export, which the phone runs, agrees with it to cosine >= 0.999 (export_clip.py checks that).

Rows are COCO train2017 images in id order, so the first n rows are the same for every size, and
the run resumes where it stopped. Queries are the first caption of 21 val2017 images (seed 90):
real text, from photos that are not in the stored set.
"""
import argparse
import io
import json
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/eyko91_coco"
MODEL, PRETRAINED, DIM = "MobileCLIP-S2", "datacompdr", 512
ANNOTATIONS = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
IMAGE_URL = "http://images.cocodataset.org/train2017/{:012d}.jpg"
QUERIES = 21  # 1 warm-up + 20 timed, as the benchmark uses


def captions(name: str) -> dict:
    """{image id: [captions]} for train2017 or val2017, from the official annotations zip (fetched once)."""
    path = OUT / f"captions_{name}.json"
    if not path.exists():
        zipped = OUT / "annotations_trainval2017.zip"
        if not zipped.exists():
            print("fetching the COCO annotations (253 MB)...")
            urllib.request.urlretrieve(ANNOTATIONS, zipped)
        with zipfile.ZipFile(zipped) as z:
            for split in ("train2017", "val2017"):
                (OUT / f"captions_{split}.json").write_bytes(z.read(f"annotations/captions_{split}.json"))
        zipped.unlink()
    by = {}
    for a in json.loads(path.read_text(encoding="utf-8"))["annotations"]:
        by.setdefault(a["image_id"], []).append(a["caption"].strip())
    return by


def fetch(image_id: int, tries: int = 5) -> bytes:
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(IMAGE_URL.format(image_id), timeout=60) as r:
                return r.read()
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--n", type=int, default=100_000, help="photos to embed (train2017 has 118,287)")
    p.add_argument("--batch", type=int, default=64)
    p.add_argument("--workers", type=int, default=16, help="photos fetched at once")
    a = p.parse_args()

    import open_clip
    import torch
    from PIL import Image
    from timm.utils import reparameterize_model

    OUT.mkdir(parents=True, exist_ok=True)
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED, device="cpu")
    model = reparameterize_model(model.eval()).eval()
    tokenizer = open_clip.get_tokenizer(MODEL)

    queries_path = OUT / "queries_512.f32"
    if not queries_path.exists():
        val = captions("val2017")
        picked = np.random.default_rng(90).choice(sorted(val), QUERIES, replace=False)
        texts = [val[int(i)][0] for i in picked]
        with torch.no_grad():
            q = torch.nn.functional.normalize(model.encode_text(tokenizer(texts)), dim=-1).numpy()
        q.astype("<f4").tofile(queries_path)
        (OUT / "queries.json").write_text(json.dumps([{"val_image_id": int(i), "caption": t} for i, t in zip(picked, texts)], indent=1) + "\n", encoding="utf-8")
        print("queries:", *texts[:3], "...", sep="\n  ")

    ids = sorted(captions("train2017"))[: a.n]
    vec_path, id_path = OUT / "images_512.f32", OUT / "image_ids.txt"
    done = len(id_path.read_text().split()) if id_path.exists() else 0
    if vec_path.exists() and vec_path.stat().st_size != done * DIM * 4:
        sys.exit(f"{vec_path} and {id_path} disagree; delete both to start again")
    print(f"{done} of {len(ids)} already embedded")
    start, last = time.perf_counter(), done
    with ThreadPoolExecutor(a.workers) as pool, vec_path.open("ab") as vf, id_path.open("a") as idf:
        for b in range(done, len(ids), a.batch):
            chunk = ids[b : b + a.batch]
            pictures = [preprocess(Image.open(io.BytesIO(raw)).convert("RGB")) for raw in pool.map(fetch, chunk)]
            with torch.no_grad():
                v = torch.nn.functional.normalize(model.encode_image(torch.stack(pictures)), dim=-1).numpy()
            vf.write(v.astype("<f4").tobytes())
            idf.write("".join(f"{i}\n" for i in chunk))
            vf.flush(), idf.flush()
            n = b + len(chunk)
            if n // 1000 > last // 1000 or n == len(ids):
                rate = (n - done) / (time.perf_counter() - start)
                print(f"{n:>7} / {len(ids)}  {rate:.1f} photos/s  ~{(len(ids) - n) / rate / 3600:.1f} h left", flush=True)
                last = n
    print(f"written: {vec_path} ({len(ids)} x {DIM}), {queries_path} ({QUERIES} x {DIM})")


if __name__ == "__main__":
    main()
