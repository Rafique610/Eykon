"""Score the laptop copy of the phone pipeline (ego4d_pipeline) on Ego4D episodic memory, per area (card EYKO-55).
    task ego4d-eval                      writes docs/results/ego4d/baseline-<date>.json and prints the tables

Rules, fixed before any score was read (20 October 2026):
  Times are seconds from the start of each downloaded clip (the annotations' clip_* fields; VQ frame numbers
  are at the clip's 5 fps). A kept frame stands for its 3 s slot, so a frame at t answers the window
  [t - 1.5, t + 1.5].
  NLQ (Objects + Place templates = "objects", People = "people"): the question goes through the app's
  search exactly (MobileCLIP-S2 text vector, cosine with every kept frame's vector, best first).
    R@k tIoU>=x   one of the first k frames' windows overlaps the answer window by at least x (Ego4D's rule)
    hit@k         one of the first k frames lies inside the answer window widened by 1.5 s each side
    chance@1      the share of kept frames inside that widened window (what a random kept frame scores)
  VQ ("when did I last see this?"): the query crop (square around the given box, as the app crops) is
  embedded with MobileCLIP; among object crops the app made in kept frames before the query moment, the
  latest one with cosine >= 0.87 (the app's same-object rule) is the answer; with none, the most alike one.
    success       the answer frame lies inside the response track, widened by 1.5 s each side
    seen          the object was ever cropped: some crop in a frame inside the widened track has cosine >= 0.87
  MQ (actions, social, mobility): the app's per-frame action, joined into segments of consecutive kept
  frames with the same action. MQ classes map to our 8 prompts only where the meaning is the same
  (MAP below); every other class is "not covered".
    found         a kept frame inside the true segment carries the mapped action
    R@1 tIoU>=0.5 some predicted segment of that action overlaps the true one by at least 0.5
    precision     of kept frames labelled with the action, the share inside a true segment of a mapped class
  No mAP: the app keeps only the winning prompt, not a score per class, so segments cannot be ranked.
"""
import datetime
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import open_clip

from src.benchmarks.ego4d_pipeline import CLIPS, EGO, MODELS, RUN, crop_square, embed

ANN = EGO / "v2/annotations"
TEXT_MODEL = Path("D:/eykon-cache/models/mobileclip_s2_text.onnx")
OUT = Path("docs/results/ego4d")
HALF, SAME = 1.5, 0.87
MAP = {  # Ego4D MQ class -> the app's action prompt, only where the meaning is the same
    "use_a_laptop_/_computer": "typing on a laptop",
    "read_a_book_/_magazine_/_shopping_list_etc.": "reading",
    "eat_a_snack": "eating",
    "converse_/_interact_with_someone": "talking to someone",
    "stir_/_mix_food_while_cooking": "cooking",
    "stir_/_mix_ingredients_in_a_bowl_or_pan_(before_cooking)": "cooking",
    "taste_food_while_cooking": "cooking",
    "walk_down_stairs_/_walk_up_stairs": "walking",
}
AREA = {"converse_/_interact_with_someone": "social", "walk_down_stairs_/_walk_up_stairs": "mobility"}
WANTED = ("drink_beverage", "use_phone", "wash_dishes_/_utensils_/_bakeware_etc.", "write_notes_in_a_paper_/_book",
          '"cut_/_chop_/_slice_a_vegetable,_fruit,_or_meat"')


def clips(task: str) -> dict:
    sel = set((EGO / "selection/clip_uids.txt").read_text().split())
    return {c["clip_uid"]: c for v in json.loads((ANN / f"{task}_val.json").read_text())["videos"] for c in v["clips"]
            if c["clip_uid"] in sel and (RUN / f"{c['clip_uid']}.json").exists()}  # only clips the pipeline has run


def run_of(uid: str) -> tuple[list[dict], np.ndarray, np.ndarray]:
    meta = json.loads((RUN / f"{uid}.json").read_text())
    vec = np.load(RUN / f"{uid}.npz")
    return meta["kept"], vec["image"], vec["crops"]


def tiou(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    return inter / (max(a[1], b[1]) - min(a[0], b[0]) + 1e-9)


def nlq() -> dict:
    tok = open_clip.get_tokenizer("MobileCLIP-S2")
    text = ort.InferenceSession(str(TEXT_MODEL), providers=["CPUExecutionProvider"])
    rows = defaultdict(list)
    for uid, clip in clips("nlq").items():
        kept, image, _ = run_of(uid)
        times = np.array([k["t"] for k in kept])
        for ann in clip["annotations"]:
            for q in ann["language_queries"]:
                if not q.get("query") or q.get("clip_start_sec") is None:
                    continue
                area = "people" if (q.get("template") or "").startswith("People") else "objects"
                gt = (q["clip_start_sec"], q["clip_end_sec"])
                v = text.run(None, {"tokens": tok([q["query"]]).numpy().astype(np.int64)})[0][0]
                order = np.argsort(-(image @ v))
                wins = [(times[i] - HALF, times[i] + HALF) for i in order[:5]]
                inside = (times >= gt[0] - HALF) & (times <= gt[1] + HALF)
                rows[area].append({
                    **{f"R@{k} tIoU>={x}": any(tiou(w, gt) >= x for w in wins[:k]) for k in (1, 5) for x in (0.3, 0.5)},
                    "hit@1": bool(inside[order[0]]), "hit@5": bool(inside[order[:5]].any()), "chance@1": float(inside.mean()),
                })
    return {a: {k: round(100 * float(np.mean([r[k] for r in rs])), 1) for k in rs[0]} | {"n": len(rs)} for a, rs in rows.items()}


def frame_at(uid: str, t: float) -> np.ndarray:
    cap = cv2.VideoCapture(str(CLIPS / f"{uid}.mp4"))
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"{uid}: no frame at {t:.1f} s")
    return frame


def vq() -> dict:
    session = ort.InferenceSession(str(MODELS["clip"]), providers=["CPUExecutionProvider"])
    rows = []
    for uid, clip in clips("vq").items():
        kept, _, crops = run_of(uid)
        fps = clip["clip_fps"]
        for ann in clip["annotations"]:
            for q in ann["query_sets"].values():
                if not q.get("is_valid") or not q.get("response_track"):
                    continue
                vc = q["visual_crop"]
                frame = frame_at(uid, vc["frame_number"] / fps)
                sx, sy = frame.shape[1] / vc["original_width"], frame.shape[0] / vc["original_height"]
                sq = crop_square([vc["x"] * sx, vc["y"] * sy, (vc["x"] + vc["width"]) * sx, (vc["y"] + vc["height"]) * sy], frame.shape[1], frame.shape[0])
                if sq is None:
                    continue
                x, y, side = sq
                v = embed(session, frame[y:y + side, x:x + side])
                track = (min(r["frame_number"] for r in q["response_track"]) / fps - HALF, max(r["frame_number"] for r in q["response_track"]) / fps + HALF)
                before = [(k["t"], float(crops[o["crop"]] @ v)) for k in kept if k["t"] < q["query_frame"] / fps
                          for o in k["objects"] if o.get("crop") is not None]
                same = [b for b in before if b[1] >= SAME]
                answer = max(same)[0] if same else (max(before, key=lambda b: b[1])[0] if before else None)
                rows.append({"success": answer is not None and track[0] <= answer <= track[1],
                             "seen": any(track[0] <= t <= track[1] and c >= SAME for t, c in before),
                             "title": q.get("object_title", "")})
    return {"objects (last seen)": {"success": round(100 * np.mean([r["success"] for r in rows]), 1),
                                    "seen": round(100 * np.mean([r["seen"] for r in rows]), 1), "n": len(rows)}}


def mq() -> dict:
    per = defaultdict(list)
    precision = defaultdict(lambda: [0, 0])
    for uid, clip in clips("moments").items():
        kept, _, _ = run_of(uid)
        truth = [(lab["label"], lab["start_time"], lab["end_time"]) for a in clip["annotations"] for lab in a["labels"] if lab.get("primary", True)]
        segs, cur = [], None
        for k in kept:
            if cur and cur[0] == k["action"]:
                cur[2] = k["t"]
            else:
                if cur and cur[0]:
                    segs.append(tuple(cur))
                cur = [k["action"], k["t"], k["t"]]
        if cur and cur[0]:
            segs.append(tuple(cur))
        for label, s, e in truth:
            if label not in MAP and label not in WANTED:
                continue
            act = MAP.get(label)
            found = act is not None and any(s <= k["t"] <= e and k["action"] == act for k in kept)
            r1 = act is not None and any(a == act and tiou((a0 - HALF, a1 + HALF), (s, e)) >= 0.5 for a, a0, a1 in segs)
            per[label].append((found, r1))
        for k in kept:
            if k["action"] in MAP.values():  # actions with no matching MQ class cannot be scored
                classes = [lab for lab, act in MAP.items() if act == k["action"]]
                precision[k["action"]][1] += 1
                precision[k["action"]][0] += any(lab in classes and s <= k["t"] <= e for lab, s, e in truth)
    table = {}
    for label, rs in sorted(per.items(), key=lambda x: -len(x[1])):
        table[label] = {"area": AREA.get(label, "actions"), "ours": MAP.get(label, "not covered"), "n": len(rs),
                        "found": round(100 * np.mean([r[0] for r in rs]), 1) if label in MAP else None,
                        "R@1 tIoU>=0.5": round(100 * np.mean([r[1] for r in rs]), 1) if label in MAP else None}
    prec = {a: {"labelled frames": t, "precision": round(100 * h / t, 1)} for a, (h, t) in precision.items()}
    return {"classes": table, "precision by action": prec}


def main() -> None:
    result = {"date": str(datetime.date.today()), "nlq": nlq(), "vq": vq(), "mq": mq()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"baseline-{result['date']}.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
