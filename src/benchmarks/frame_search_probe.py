"""Laptop probe ahead of card EYKO-19: can a typed phrase find the frames that show a thing,
using only the frames' MobileCLIP vectors? Run:

    task probe-frame-search -- <frames folder> <presence csv> [<phone perception json>]

Rules, fixed before any search ran:
  For each phrase, all frames are ranked by how alike their vector is to the phrase's vector.
  top 5        how many of the first five frames really show the thing (out of five, or out of
               the number of frames that show it when that is smaller)
  avg precision the usual ranking score: 1.0 means every frame with the thing comes before every
               frame without it
  chance       the share of frames that show the thing: what a random order would score
  The phone's detector, when its json is given, is scored on the same labels as "frames it
  listed the thing in": how many of those are right, and how many of the true frames it found.
The presence labels are per frame: the thing is visible and recognisable in that frame alone.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image
from timm.utils import reparameterize_model

MODEL, PRETRAINED = "MobileCLIP-S2", "datacompdr"
PHRASES = {  # column in the presence csv: (phrase as typed, the detector's own name for it or None)
    "phone": ("a phone", "cell phone"),
    "laptop": ("a laptop", "laptop"),
    "chair": ("a chair", "chair"),
    "backpack": ("a backpack", "backpack"),
    "car": ("a car", "car"),
    "monitor": ("a computer monitor", "tv"),
    "papers": ("sheets of paper", None),
    "table_tennis": ("a table tennis table", None),
}


def average_precision(order: np.ndarray, relevant: np.ndarray) -> float:
    hits = relevant[order]
    return float((np.cumsum(hits) / (np.arange(len(hits)) + 1))[hits.astype(bool)].mean())


def main() -> None:
    frames_dir, presence_csv = Path(sys.argv[1]), sys.argv[2]
    rows = list(csv.DictReader(open(presence_csv, encoding="utf-8")))
    names = [r["frame"] for r in rows]
    detector = {f["frame"][:-4]: [o["label"] for o in f["objects"]] for f in json.load(open(sys.argv[3]))["frames"]} if len(sys.argv) > 3 else None

    model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED, device="cpu")
    model = reparameterize_model(model.eval())
    tokenizer = open_clip.get_tokenizer(MODEL)
    unit = lambda x: torch.nn.functional.normalize(x, dim=-1).numpy()  # noqa: E731
    with torch.no_grad():
        images = unit(model.encode_image(torch.stack([preprocess(Image.open(frames_dir / f"{n}.jpg").convert("RGB")) for n in names])))
        plain = unit(model.encode_text(tokenizer([p for p, _ in PHRASES.values()])))
        photo = unit(model.encode_text(tokenizer([f"a photo of {p}" for p, _ in PHRASES.values()])))

    print(f"{len(names)} frames, {MODEL}; phrase as typed | with 'a photo of' in front")
    print(f"{'thing':14}{'frames':>7}{'chance':>8} | {'top 5':>6}{'avg prec':>9} | {'top 5':>6}{'avg prec':>9} | detector: listed, right, found")
    for i, (column, (phrase, label)) in enumerate(PHRASES.items()):
        relevant = np.array([int(r[column]) for r in rows])
        line = f"{column:14}{relevant.sum():>7}{relevant.mean():>8.2f}"
        for texts in (plain, photo):
            order = np.argsort(-(images @ texts[i]))
            line += f" | {relevant[order[:5]].sum()} of {min(5, relevant.sum())}{average_precision(order, relevant):>9.2f}"
        if detector and label:
            listed = np.array([int(label in detector[n]) for n in names])
            right = int((listed & relevant).sum())
            line += f" | {listed.sum()} listed, {right} right, {right} of {relevant.sum()} found"
        elif detector:
            line += " | not a class the detector has"
        print(line)
        top = np.argsort(-(images @ plain[i]))[:5]
        print(f"{'':14}first five for '{phrase}': " + ", ".join(f"{names[j]}{'' if relevant[j] else ' (no)'}" for j in top))


if __name__ == "__main__":
    main()
