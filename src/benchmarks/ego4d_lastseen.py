"""'When did I last see this?' with crops of any object (card EYKO-62), scored with ego4d_eval's VQ rules.
    task ego4d-lastseen -- [A|B]

Fixed before scoring (20 October 2026):
  frames    the kept frames of the app run (ego4d_pipeline), decoded again at the same time and size
  crops     app        the app's own crops (YOLOX + D-FINE + YOLOE own words), already in the run
            anything   YOLOE-11S prompt-free (Ultralytics, AGPL, academic): its 10 surest boxes >= 0.10 per frame
            both       app + anything
  vectors   mobileclip the app's crop vector (MobileCLIP-S2 on the square crop)
            dinov2     DINOv2-S (facebook/dinov2-small) [CLS] vector of the same square crop, length 1
  answer    the latest crop before the query frame with cosine >= T, else the most alike one (the app's rule);
            T is chosen on set A from a fixed list per vector kind and only reported on set B
Cost per frame is printed (laptop CPU), so a phone port can be judged.
"""
import json
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort
import torch
from transformers import AutoImageProcessor, AutoModel
from ultralytics import YOLOE

from src.benchmarks import ego4d_eval as ev
from src.benchmarks.ego4d_pipeline import CLIPS, EGO, FRAME_MAX, MODELS, crop_square, embed

PF = "D:/eykon-cache/bench/detectors/yoloe-11s-seg-pf.pt"
CACHE = EGO / "lastseen"
TS = {"mobileclip": (0.75, 0.80, 0.85, 0.87, 0.90), "dinov2": (0.40, 0.50, 0.60, 0.70, 0.80)}
TOP, MIN_CONF = 10, 0.10


def frame_at(cap, t: float) -> np.ndarray:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    if not ok:
        raise RuntimeError(f"no frame at {t:.2f} s")
    k = max(1, int(np.ceil(max(f.shape[:2]) / FRAME_MAX)))
    return f[::k, ::k][: f.shape[0] // k // 2 * 2, : f.shape[1] // k // 2 * 2]


class Vectors:
    def __init__(self):
        torch.set_num_threads(6)
        self.clip = ort.InferenceSession(str(MODELS["clip"]), providers=["CPUExecutionProvider"])
        self.prep = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
        self.dino = AutoModel.from_pretrained("facebook/dinov2-small").eval()

    def many(self, bgr: np.ndarray, boxes: list) -> list[dict | None]:
        """Vectors for every box of one frame; DINOv2 runs once on all crops together."""
        squares = [crop_square(b, bgr.shape[1], bgr.shape[0]) for b in boxes]
        crops = [bgr[y:y + side, x:x + side] for x, y, side in (q for q in squares if q is not None)]
        if not crops:
            return [None] * len(boxes)
        with torch.no_grad():
            d = self.dino(**self.prep(images=[c[:, :, ::-1].copy() for c in crops], return_tensors="pt")).last_hidden_state[:, 0].numpy()
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        it = iter(range(len(crops)))
        out = []
        for q in squares:
            if q is None:
                out.append(None)
                continue
            i = next(it)
            out.append({"mobileclip": embed(self.clip, crops[i]), "dinov2": d[i]})
        return out

    def __call__(self, bgr: np.ndarray, box) -> dict | None:
        return self.many(bgr, [box])[0]


def crops_of(uid: str, kept: list[dict], vec: Vectors, pf) -> dict:
    """Times and vectors of every crop in the clip's kept frames, per crop kind; cached on D:."""
    file = CACHE / f"{uid}.npz"
    if file.exists():
        z = np.load(file)
        return {k: z[k] for k in z.files}
    cap = cv2.VideoCapture(str(CLIPS / f"{uid}.mp4"))
    rows = {"t": [], "kind": [], "mobileclip": [], "dinov2": []}
    start = time.time()
    for k in kept:
        f = frame_at(cap, k["t"])
        boxes = [("app", o["box"]) for o in k["objects"]]
        r = pf.predict(f, conf=MIN_CONF, verbose=False)[0]
        order = np.argsort(-r.boxes.conf.numpy())[:TOP]
        boxes += [("anything", r.boxes.xyxy.numpy()[i].tolist()) for i in order]
        for (kind, _), v in zip(boxes, vec.many(f, [b for _, b in boxes]), strict=True):
            if v is not None:
                rows["t"].append(k["t"])
                rows["kind"].append(kind)
                rows["mobileclip"].append(v["mobileclip"])
                rows["dinov2"].append(v["dinov2"])
    cap.release()
    out = {"t": np.array(rows["t"]), "kind": np.array(rows["kind"]), "mobileclip": np.array(rows["mobileclip"]),
           "dinov2": np.array(rows["dinov2"]), "seconds_per_frame": np.array(time.time() - start) / max(1, len(kept))}
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(file, **out)
    return out


def main(which: str = "A") -> None:
    ev.SET = which
    vec, pf = Vectors(), YOLOE(PF)
    queries = []
    for uid, clip in ev.clips("vq").items():
        kept, _, _ = ev.run_of(uid)
        crops = crops_of(uid, kept, vec, pf)
        cap = cv2.VideoCapture(str(CLIPS / f"{uid}.mp4"))
        fps = clip["clip_fps"]
        for ann in clip["annotations"]:
            for q in ann["query_sets"].values():
                if not q.get("is_valid") or not q.get("response_track"):
                    continue
                vc = q["visual_crop"]
                f = frame_at(cap, vc["frame_number"] / fps)
                sx, sy = f.shape[1] / vc["original_width"], f.shape[0] / vc["original_height"]
                qv = vec(f, [vc["x"] * sx, vc["y"] * sy, (vc["x"] + vc["width"]) * sx, (vc["y"] + vc["height"]) * sy])
                if qv is None:
                    continue
                track = (min(r["frame_number"] for r in q["response_track"]) / fps - ev.HALF, max(r["frame_number"] for r in q["response_track"]) / fps + ev.HALF)
                queries.append((crops, qv, q["query_frame"] / fps, track))
        cap.release()
    result = {"queries": len(queries), "seconds per frame (YOLOE-PF + both vectors, laptop)":
              round(float(np.mean([np.load(CACHE / f"{u}.npz")["seconds_per_frame"] for u in ev.clips("vq")])), 2)}
    for kinds in (("app",), ("anything",), ("app", "anything")):
        for space, ts in TS.items():
            for t in ts:
                ok, seen = [], []
                for crops, qv, at, track in queries:
                    use = np.isin(crops["kind"], kinds) & (crops["t"] < at)
                    if not use.any():
                        ok.append(False)
                        seen.append(False)
                        continue
                    times, sims = crops["t"][use], crops[space][use] @ qv[space]
                    answer = times[sims >= t].max() if (sims >= t).any() else times[sims.argmax()]
                    ok.append(track[0] <= answer <= track[1])
                    seen.append(bool(((times >= track[0]) & (times <= track[1]) & (sims >= t)).any()))
                result["+".join(kinds) + f" {space} T{t}"] = {"success": round(100 * np.mean(ok), 1), "seen": round(100 * np.mean(seen), 1)}
    for k, r in sorted(((k, r) for k, r in result.items() if isinstance(r, dict)), key=lambda kv: -kv[1]["success"])[:12]:
        print(f"success {r['success']:5.1f}  seen {r['seen']:5.1f}  {k}")
    print({k: v for k, v in result.items() if not isinstance(v, dict)})
    ev.OUT.mkdir(parents=True, exist_ok=True)
    (ev.OUT / f"lastseen-{which}.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:])
