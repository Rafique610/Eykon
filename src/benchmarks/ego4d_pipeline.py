"""Laptop copy of the phone's video pipeline, run on the Ego4D clips (card EYKO-55).
    task ego4d-pipeline -- [<clip uid> ...]      default: every clip in D:/eykon-cache/ego4d/selection/clip_uids.txt

Same ONNX files, same constants and the same order of steps as the app (android/.../video/), so the
accuracy measured here is the app's; EYKO-56 checks that against the Pixel on a sample.
  split          3 frames a second, the first decoded frame at or after each time, shrunk by a whole
                 factor to at most 640 px, JPEG 90                         (VideoSplit.kt, FrameExtractor.kt)
  filter         9-frame slots: the sharpest frame that is neither dark nor bright, then dark / bright /
                 blurry / still checks against the last kept frame     (FrameFilters.kt pickSlot, check)
  dedup          dHash within 6 bits of any unique frame, else MobileCLIP cosine >= 0.95 (VideoDedup.kt)
  scene          YOLOX-Tiny >= 0.35 + D-FINE S >= 0.5 (its "person" dropped), merged; place and action
                 = best MobileCLIP prompt if its share >= 0.30                  (OptionA.kt)
  small_objects  YOLOE-11L, keys and earbuds only, >= 0.25, one box each   (YoloeDetector.kt)
  caption        personal things first, three things in all, people, place, action (VideoScene.kt)
  latest         a MobileCLIP vector for each object's square crop (boxes under 16 px skipped) (VideoLatest.kt)
Not run: audio, the keyword index and caption vectors (search does not use them yet).
Output per clip: D:/eykon-cache/ego4d/run/<clip>.json (frames, objects, captions) and .npz (vectors).
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from src.benchmarks import perception_golden as yolox

EGO = Path("D:/eykon-cache/ego4d")
CLIPS, RUN = EGO / "v2/clips", EGO / "run"
ASSETS = Path("android/app/src/main/assets")
MODELS = {
    "yolox": Path("models/yolox_tiny.onnx"),
    "dfine": Path("D:/eykon-cache/bench/detectors/hybrid_phone/dfine_s_obj365.onnx"),
    "yoloe": Path("D:/eykon-cache/bench/detectors/yoloe_phone/yoloe-11l-seg.onnx"),
    "clip": Path("D:/eykon-cache/models/mobileclip_s2_image.onnx"),
}
FPS, FRAME_MAX, JPEG, SMALL_SIDE, SLOT = 3.0, 640, 90, 320, 9
DARK, BRIGHT, BLUR, DIFF, HIST = 25.0, 235.0, 60.0, 6.0, 0.10
HASH_MAX, COS_MIN = 6, 0.95
YOLOX_MIN, DFINE_MIN, YOLOE_MIN, PROMPT_MIN = 0.35, 0.5, 0.25, 0.30
MIN_BOX = 16
PERSONAL = {"keys", "earbuds", "wallet", "glasses", "pen", "cell phone", "remote", "watch", "earphone", "handbag", "umbrella"}
THREADS = 3


def split(path: Path) -> tuple[list[float], list[np.ndarray]]:
    cap = cv2.VideoCapture(str(path))
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    wanted = [i / FPS for i in range(int(np.ceil(duration * FPS - 1e-6)))]
    times, frames, n = [], [], 0
    while n < len(wanted):
        ok, frame = cap.read()
        if not ok:
            break
        if cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 < wanted[n] - 1e-3:
            continue
        k = max(1, int(np.ceil(max(frame.shape[:2]) / FRAME_MAX)))
        frame = frame[::k, ::k][: frame.shape[0] // k // 2 * 2, : frame.shape[1] // k // 2 * 2]
        frames.append(cv2.imdecode(cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG])[1], cv2.IMREAD_COLOR))
        times.append(wanted[n])
        n += 1
    cap.release()
    return times, frames


def small_gray(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    k = max(1, round(max(gray.shape) / SMALL_SIDE))
    h, w = gray.shape[0] // k, gray.shape[1] // k
    return cv2.resize(gray[: h * k, : w * k], (w, h), interpolation=cv2.INTER_AREA)


def sharpness(g: np.ndarray) -> float:
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def check(prev: np.ndarray | None, g: np.ndarray) -> str | None:
    b = g.mean()
    if b < DARK:
        return "dark"
    if b > BRIGHT:
        return "bright"
    if sharpness(g) < BLUR:
        return "blurry"
    hist = lambda x: cv2.calcHist([x], [0], None, [64], [0, 256])
    if prev is not None and prev.shape == g.shape and cv2.absdiff(prev, g).mean() < DIFF and \
            cv2.compareHist(hist(prev), hist(g), cv2.HISTCMP_BHATTACHARYYA) < HIST:
        return "still"
    return None


def filter_slots(grays: list[np.ndarray]) -> list[str | None]:
    reasons: list[str | None] = []
    prev = None
    for s in range(0, len(grays), SLOT):
        slot = grays[s:s + SLOT]
        r: list[str | None] = ["dark" if g.mean() < DARK else "bright" if g.mean() > BRIGHT else "less sharp" for g in slot]
        candidates = [i for i in range(len(slot)) if r[i] == "less sharp"]
        if candidates:
            best = max(candidates, key=lambda i: sharpness(slot[i]))
            r[best] = check(prev, slot[best])
            if r[best] is None:
                prev = slot[best]
        reasons += r
    return reasons


def dhash(g: np.ndarray) -> int:
    tiny = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
    return int("".join("1" if b else "0" for b in (tiny[:, 1:] > tiny[:, :-1]).flatten()), 2)


def embed(session, bgr: np.ndarray) -> np.ndarray:
    scale = 256 / min(bgr.shape[:2])
    w, h = max(256, round(bgr.shape[1] * scale)), max(256, round(bgr.shape[0] * scale))
    img = cv2.resize(bgr, (w, h), interpolation=cv2.INTER_LINEAR)[(h - 256) // 2:(h - 256) // 2 + 256, (w - 256) // 2:(w - 256) // 2 + 256]
    return session.run(None, {"image": np.ascontiguousarray(img[:, :, ::-1].transpose(2, 0, 1)[None], dtype=np.float32) / 255})[0][0]


def dedup(frames, grays, reasons, clip) -> dict[int, np.ndarray]:
    unique: list[tuple[int, int, np.ndarray]] = []
    for i, r in enumerate(reasons):
        if r is not None:
            continue
        h = dhash(grays[i])
        near = min(unique, key=lambda u: (u[1] ^ h).bit_count(), default=None)
        if near and (near[1] ^ h).bit_count() <= HASH_MAX:
            reasons[i] = f"duplicate of {near[0]}"
            continue
        v = embed(clip, frames[i])
        same = max(unique, key=lambda u: float(u[2] @ v), default=None)
        if same and float(same[2] @ v) >= COS_MIN:
            reasons[i] = f"duplicate of {same[0]}"
        else:
            unique.append((i, h, v))
    return {i: v for i, _, v in unique}


def plain(name: str) -> str:
    n = name.split("/")[0].strip().lower()
    return "keys" if n == "key" else n


def dfine_detect(session, labels, bgr: np.ndarray) -> list[dict]:
    rgb = cv2.resize(bgr, (640, 640), interpolation=cv2.INTER_LINEAR)[:, :, ::-1]
    logits, boxes = session.run(["logits", "pred_boxes"], {"pixel_values": np.ascontiguousarray(rgb.transpose(2, 0, 1)[None], dtype=np.float32) / 255})
    out, (h, w) = [], bgr.shape[:2]
    for q in range(logits.shape[1]):
        c = int(logits[0, q].argmax())
        conf = float(1 / (1 + np.exp(-logits[0, q, c])))
        if conf >= DFINE_MIN and plain(labels[c]) != "person":
            cx, cy, bw, bh = boxes[0, q]
            out.append({"label": plain(labels[c]), "conf": conf, "box": [float((cx - bw / 2) * w), float((cy - bh / 2) * h), float((cx + bw / 2) * w), float((cy + bh / 2) * h)], "source": "detector"})
    return out


def yoloe_detect(session, words, bgr: np.ndarray) -> list[dict]:
    h, w = bgr.shape[:2]
    r = min(640 / w, 640 / h)
    nw, nh = round(w * r), round(h * r)
    left, top = round((640 - nw) / 2 - 0.1), round((640 - nh) / 2 - 0.1)
    canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
    canvas[top:top + nh, left:left + nw] = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR) if (nw, nh) != (w, h) else bgr
    rows = session.run(["output0"], {"images": np.ascontiguousarray(canvas[:, :, ::-1].transpose(2, 0, 1)[None], dtype=np.float32) / 255})[0][0]
    out = []
    for c, name in enumerate(words["names"]):
        if name not in words["use"]:
            continue
        j = int(rows[4 + c].argmax())
        if rows[4 + c, j] < YOLOE_MIN:
            continue
        cx, cy, bw, bh = (float(v) for v in rows[:4, j])
        fx = lambda v: min(max((v - left) / r, 0.0), float(w))
        fy = lambda v: min(max((v - top) / r, 0.0), float(h))
        out.append({"label": name, "conf": float(rows[4 + c, j]), "box": [fx(cx - bw / 2), fy(cy - bh / 2), fx(cx + bw / 2), fy(cy + bh / 2)], "source": "own"})
    return out


def best_prompt(vector: np.ndarray, prompts: dict) -> str | None:
    p = yolox.probabilities(vector, np.array(list(prompts.values())))
    return list(prompts)[int(p.argmax())] if p.max() >= PROMPT_MIN else None


def caption(objects: list[dict], people: int, place: str | None, action: str | None) -> str:
    names: dict[str, bool] = {}  # first (surest) sighting of each name decides, like distinctBy
    for o in sorted(objects, key=lambda o: -o["conf"]):
        names.setdefault(o["label"], o["source"] == "own" or o["label"] in PERSONAL)
    names = list(names.items())
    personal = [n for n, p in names if p]
    labels = personal + [n for n, p in names if not p][: max(0, 3 - len(personal))]
    parts = [] if not labels else [" and ".join(labels)] if len(labels) <= 2 else [", ".join(labels[:-1]) + " and " + labels[-1]]
    if people:
        parts.append("1 person" if people == 1 else f"{people} people")
    if place:
        parts.append(place if place.startswith("inside ") else f"in {place}")
    if action:
        parts.append(action)
    return ", ".join(parts) or "nothing recognised"


def crop_square(box, w, h):
    left, top, right, bottom = max(0.0, box[0]), max(0.0, box[1]), min(float(w), box[2]), min(float(h), box[3])
    if right - left < MIN_BOX or bottom - top < MIN_BOX:
        return None
    side = min(round(max(right - left, bottom - top)), min(w, h))
    x = min(max(round((left + right) / 2 - side / 2), 0), w - side)
    y = min(max(round((top + bottom) / 2 - side / 2), 0), h - side)
    return x, y, side


def sessions() -> dict:
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = THREADS
    return {k: ort.InferenceSession(str(p), opts, providers=["CPUExecutionProvider"]) for k, p in MODELS.items()}


def run_clip(uid: str) -> str:
    out = RUN / f"{uid}.json"
    if out.exists():
        return f"{uid[:8]} cached"
    t0 = time.time()
    s = sessions()
    prompts = json.loads((ASSETS / "scene_prompts.json").read_text(encoding="utf-8"))
    labels = json.loads((ASSETS / "dfine_labels.json").read_text(encoding="utf-8"))
    words = json.loads((ASSETS / "yoloe_words.json").read_text(encoding="utf-8"))
    times, frames = split(CLIPS / f"{uid}.mp4")
    grays = [small_gray(f) for f in frames]
    reasons = filter_slots(grays)
    vectors = dedup(frames, grays, reasons, s["clip"])
    rows, crops = [], []
    for i in sorted(vectors):
        f, h, w = frames[i], frames[i].shape[0], frames[i].shape[1]
        found = yolox.detect(s["yolox"], f, YOLOX_MIN)
        found = [dict(d, source="detector") for d in found]
        dfine = [d for d in dfine_detect(s["dfine"], labels, f)
                 if not any(y["label"] == d["label"] and yolox.iou(np.array(y["box"]), np.array(d["box"])) > 0.5 for y in found)]
        detections = found + dfine
        people = sum(d["label"] == "person" for d in detections)
        objects = [d for d in detections if d["label"] != "person"] + yoloe_detect(s["yoloe"], words, f)
        place, action = best_prompt(vectors[i], prompts["places"]), best_prompt(vectors[i], prompts["actions"])
        for o in objects:
            sq = crop_square(o["box"], w, h)
            o["crop"] = None if sq is None else len(crops)
            if sq is not None:
                x, y, side = sq
                crops.append(embed(s["clip"], f[y:y + side, x:x + side]))
        rows.append({"i": i, "t": times[i], "people": people, "place": place, "action": action, "objects": objects,
                     "caption": caption(objects, people, place, action)})
    RUN.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(RUN / f"{uid}.npz", frames=np.array(sorted(vectors)), image=np.stack([vectors[i] for i in sorted(vectors)]),
                        crops=np.stack(crops) if crops else np.zeros((0, 512), np.float32))
    drops: dict[str, int] = {}
    for r in reasons:
        key = "kept" if r is None else "duplicate" if r.startswith("duplicate") else r
        drops[key] = drops.get(key, 0) + 1
    out.write_text(json.dumps({"clip": uid, "decoded": len(frames), "times": times, "reasons": reasons, "counts": drops,
                               "kept": rows, "seconds": round(time.time() - t0, 1)}) + "\n", encoding="utf-8")
    return f"{uid[:8]} {len(frames)} frames, kept {len(rows)}, {time.time() - t0:.0f} s"


def main(uids: list[str]) -> None:
    uids = uids or (EGO / "selection/clip_uids.txt").read_text().split()
    start = time.time()
    with Pool(4) as pool:
        for line in pool.imap_unordered(run_clip, uids):
            print(line, flush=True)
    print(f"all {len(uids)} clips in {(time.time() - start) / 60:.1f} min")


if __name__ == "__main__":
    main(sys.argv[1:])
