"""Run YOLOE only on frames MobileCLIP flags for keys or earbuds (card EYKO-63, SpotEM's cheap-index idea).
    task ego4d-gate -- [A|B]

Fixed before scoring (20 October 2026):
  flag     the frame's stored MobileCLIP vector against "a photo of keys" and "a photo of earbuds" (MobileCLIP-S2
           text); YOLOE runs when the higher cosine is at least C
  own50    our 50 labelled frames (S1-01, S1-02): YOLOE-11L (the phone's ONNX, keys + earbuds, >= 0.25) on every
           frame gives the reference finds; a find is right when the frame's label says the thing is there
  Ego4D    the app run's own YOLOE finds per kept frame (no labels for keys / earbuds there)
  report   per C: share of frames YOLOE still runs on, right finds kept on own50, all finds kept on Ego4D
  C        chosen as the highest value that keeps every right own50 find, then checked on Ego4D set B
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import open_clip

from src.benchmarks import ego4d_eval as ev
from src.benchmarks.ego4d_pipeline import ASSETS, MODELS, embed, yoloe_detect

OWN = Path("D:/eykon-cache/bench/detectors/own")
LABELS = Path("docs/results/detectors/own-presence-2026-10-14.csv")
CS = (0.0, 0.15, 0.18, 0.20, 0.22, 0.24, 0.26, 0.28)


def main(which: str = "A") -> None:
    ev.SET = which
    tok = open_clip.get_tokenizer("MobileCLIP-S2")
    text = ort.InferenceSession(str(ev.TEXT_MODEL), providers=["CPUExecutionProvider"])
    t = np.stack([text.run(None, {"tokens": tok([p]).numpy().astype(np.int64)})[0][0] for p in ("a photo of keys", "a photo of earbuds")])
    clip = ort.InferenceSession(str(MODELS["clip"]), providers=["CPUExecutionProvider"])
    yoloe = ort.InferenceSession(str(MODELS["yoloe"]), providers=["CPUExecutionProvider"])
    words = json.loads((ASSETS / "yoloe_words.json").read_text(encoding="utf-8"))

    own = []  # (flag score, right finds, wrong finds)
    with open(LABELS, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        f = cv2.imread(str(OWN / f"{row['frame']}.jpg"))
        found = {d["label"] for d in yoloe_detect(yoloe, words, f)}
        right = sum(row.get(x) == "1" for x in found)
        own.append((float((embed(clip, f) @ t.T).max()), right, len(found) - right))
    ego = []  # (flag score, YOLOE finds)
    for uid in {u for task in ("nlq", "vq", "moments") for u in ev.clips(task)}:
        kept, image, _ = ev.run_of(uid)
        flags = (image @ t.T).max(1)
        ego += [(float(s), sum(o["source"] == "own" for o in k["objects"])) for s, k in zip(flags, kept, strict=True)]

    result = {"own50 frames": len(own), "own50 right finds": sum(r for _, r, _ in own), "own50 wrong finds": sum(w for _, _, w in own),
              f"Ego4D {which} frames": len(ego), f"Ego4D {which} finds": sum(n for _, n in ego), "by C": {}}
    for c in CS:
        o = [x for x in own if x[0] >= c]
        e = [x for x in ego if x[0] >= c]
        result["by C"][c] = {"own50 frames run %": round(100 * len(o) / len(own), 1), "own50 right finds kept": sum(r for _, r, _ in o),
                             "own50 wrong finds kept": sum(w for _, _, w in o), f"Ego4D {which} frames run %": round(100 * len(e) / len(ego), 1),
                             f"Ego4D {which} finds kept": sum(n for _, n in e)}
        print(c, result["by C"][c], flush=True)
    print({k: v for k, v in result.items() if k != "by C"})
    ev.OUT.mkdir(parents=True, exist_ok=True)
    (ev.OUT / f"gate-{which}.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:])
