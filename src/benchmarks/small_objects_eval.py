"""Laptop measurement for card EYKO-32: where should the phone look for a named small object?

    task eval-small-objects -- <epic100 folder> <hand_landmarker.task> [<out json>]

Compares, on EPIC-KITCHENS-100 take / put events labelled by people:
  hands   find hands (MediaPipe Hands), crop a square around each, name the crop      (card option 1)
  grid    no hand finder: cut the frame into tiles, name every tile                   (card option 3)
  whole   name the whole frame (one "tile")
Naming a crop is the card's rule: MobileCLIP shares over "a photo of <object>" for every listed
object plus "an empty hand" and "something else"; the top phrase counts only when it is a listed
object and its share is at least a minimum.

Everything below was fixed from the annotations before any model saw a frame:
  objects    noun classes with at least 3 take / put events in the eight videos, except "food"
  event      one frame per take / put event of a listed object: the middle of the labelled span
  no-object  the middle of every other action whose object is not listed and that has no listed
             event within 1 s (opening a drawer, pouring milk, picking up something unlisted)
  found      the event's object is among the names reported for its frame
  false alarm a no-object frame for which any name is reported
  precision  of all names reported on event frames and no-object frames, the share that are the
             frame's labelled object
  split      the keyframe trial's split: settings are picked on P02_119, P03_06, P04_14, P07_13
             (best F1, ties to the higher minimum) and reported on P11_24, P16_02, P26_11, P30_01
"""
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import open_clip
import torch
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from PIL import Image
from timm.utils import reparameterize_model

MODEL, PRETRAINED = "MobileCLIP-S2", "datacompdr"
TUNE = {"P02_119", "P03_06", "P04_14", "P07_13"}
MIN_EVENTS = 3
NAMES = {  # EPIC noun class -> the name a person would type
    "10": "a glass", "5": "a pan", "2": "a plate", "1": "a spoon", "7": "a bowl",
    "20": "a spatula", "4": "a knife", "18": "a chopping board", "23": "a box",
}
OTHERS = ["an empty hand", "something else"]
MINIMUMS = [round(0.30 + 0.05 * i, 2) for i in range(14)]  # 0.30 ... 0.95
HAND_SCALES = [1.5, 2.0, 3.0]


def seconds(stamp: str) -> float:
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def load_frames(root: Path) -> tuple[list[dict], list[str]]:
    """Event frames and no-object frames, from the annotations alone."""
    videos = [r["video_id"] for r in csv.DictReader(open(root / "selection.csv"))]
    actions = [
        r for name in ("EPIC_100_train.csv", "EPIC_100_validation.csv")
        for r in csv.DictReader(open(root / "annotations" / name, encoding="utf-8")) if r["video_id"] in videos
    ]
    for a in actions:
        a["mid"] = (seconds(a["start_timestamp"]) + seconds(a["stop_timestamp"])) / 2
        a["handled"] = a["verb_class"] in ("0", "1")  # EPIC verb classes: 0 take, 1 put
    counts = Counter(a["noun_class"] for a in actions if a["handled"])
    listed = [c for c, n in counts.most_common() if n >= MIN_EVENTS and c != "34"]  # 34 is "food"
    assert set(listed) == set(NAMES), (listed, counts.most_common(12))
    events = [a for a in actions if a["handled"] and a["noun_class"] in listed]
    frames = [{"video": a["video_id"], "t": a["mid"], "object": NAMES[a["noun_class"]], "what": a["narration"]} for a in events]
    for a in actions:
        near = any(e["video_id"] == a["video_id"] and abs(e["mid"] - a["mid"]) <= 1.0 for e in events)
        if a["noun_class"] not in listed and not near:
            frames.append({"video": a["video_id"], "t": a["mid"], "object": None, "what": a["narration"]})
    return frames, [NAMES[c] for c in listed]


def read_pictures(root: Path, frames: list[dict]) -> None:
    for video in sorted({f["video"] for f in frames}):
        capture = cv2.VideoCapture(str(root / "clips" / f"{video}.mp4"))
        for f in sorted((f for f in frames if f["video"] == video), key=lambda f: f["t"]):
            capture.set(cv2.CAP_PROP_POS_MSEC, f["t"] * 1000)
            ok, bgr = capture.read()
            assert ok, (video, f["t"])
            f["rgb"] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        capture.release()


def grid(width: int, height: int, side: int, columns: int, rows: int) -> list[tuple[int, int, int]]:
    xs = np.linspace(0, width - side, columns).round().astype(int)
    ys = np.linspace(0, height - side, rows).round().astype(int)
    return [(int(x), int(y), side) for y in ys for x in xs]


def hand_boxes(finder, rgb: np.ndarray, enlarge: int = 1) -> list[tuple[float, float, float]]:
    """Centre x, centre y and longer side of each hand found, in the frame's own pixels."""
    h, w = rgb.shape[:2]
    picture = cv2.resize(rgb, None, fx=enlarge, fy=enlarge, interpolation=cv2.INTER_CUBIC) if enlarge != 1 else rgb
    result = finder.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(picture)))
    boxes = []
    for hand in result.hand_landmarks:
        xs, ys = [p.x * w for p in hand], [p.y * h for p in hand]
        boxes.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(max(xs) - min(xs), max(ys) - min(ys))))
    return boxes


def square(cx: float, cy: float, side: float, width: int, height: int) -> tuple[int, int, int]:
    side = int(min(max(side, 32), width, height))
    return int(min(max(cx - side / 2, 0), width - side)), int(min(max(cy - side / 2, 0), height - side)), side


def main() -> None:
    root, hand_model = Path(sys.argv[1]), sys.argv[2]
    frames, objects = load_frames(root)
    read_pictures(root, frames)
    height, width = frames[0]["rgb"].shape[:2]
    print(f"{sum(f['object'] is not None for f in frames)} event frames, {sum(f['object'] is None for f in frames)} no-object frames, "
          f"{width}x{height}; objects: {objects}")

    finder = vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(base_options=mp_python.BaseOptions(model_asset_path=hand_model), num_hands=2))
    # Added after the first run found a hand in only 12 of 44 event frames: a far more willing
    # setting (confidence 0.1 instead of 0.5, the frame enlarged twice).
    eager = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=hand_model), num_hands=2,
        min_hand_detection_confidence=0.1, min_hand_presence_confidence=0.1))
    hand_ms = 0.0
    for f in frames:
        start = time.perf_counter()
        f["hands"] = hand_boxes(finder, f["rgb"])
        hand_ms += 1000 * (time.perf_counter() - start)
        f["eager_hands"] = hand_boxes(eager, f["rgb"], enlarge=2)

    # every way of choosing where to look: name -> crops (x, y, side) per frame
    tiles = {"whole frame": [(0, 0, 0)], "grid, 3 tiles": grid(width, height, height, 3, 1),
             "grid, 18 tiles": grid(width, height, height // 2, 6, 3)}
    tiles["grid, 3 + 18 tiles"] = tiles["grid, 3 tiles"] + tiles["grid, 18 tiles"]
    looks = {name: [crops] * len(frames) for name, crops in tiles.items()}
    for scale in HAND_SCALES:
        looks[f"hands, crop {scale} x hand"] = [[square(cx, cy, scale * side, width, height) for cx, cy, side in f["hands"]] for f in frames]
    looks["hands 2.0 x, plus the whole frame"] = [crops + [(0, 0, 0)] for crops in looks["hands, crop 2.0 x hand"]]
    for scale in (2.0, 3.0):
        looks[f"eager hands, crop {scale} x hand"] = [[square(cx, cy, scale * side, width, height) for cx, cy, side in f["eager_hands"]] for f in frames]

    model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED, device="cpu")
    model = reparameterize_model(model.eval())
    unit = lambda x: torch.nn.functional.normalize(x, dim=-1).numpy()  # noqa: E731
    with torch.no_grad():
        texts = unit(model.encode_text(open_clip.get_tokenizer(MODEL)([f"a photo of {o}" for o in objects] + OTHERS)))
    cache: dict = {}

    def shares(index: int, crop: tuple[int, int, int]) -> np.ndarray:
        if (index, crop) not in cache:
            x, y, side = crop
            rgb = frames[index]["rgb"]
            picture = Image.fromarray(rgb if side == 0 else rgb[y:y + side, x:x + side])
            with torch.no_grad():
                vector = unit(model.encode_image(preprocess(picture)[None]))[0]
            logits = 100 * vector @ texts.T
            p = np.exp(logits - logits.max())
            cache[(index, crop)] = p / p.sum()
        return cache[(index, crop)]

    def reported(index: int, crops: list, minimum: float) -> set[str]:
        names = set()
        for crop in crops:
            p = shares(index, crop)
            top = int(p.argmax())
            if top < len(objects) and p[top] >= minimum:
                names.add(objects[top])
        return names

    def score(look: str, minimum: float, which: list[int]) -> dict:
        found = events = alarms = empties = said = right = 0
        for i in which:
            names = reported(i, looks[look][i], minimum)
            truth = frames[i]["object"]
            said += len(names)
            if truth is None:
                empties += 1
                alarms += bool(names)
            else:
                events += 1
                found += truth in names
                right += truth in names
        precision = right / said if said else 0.0
        recall = found / events if events else 0.0
        return {"found": found, "events": events, "false_alarms": alarms, "no_object": empties, "names_reported": said,
                "precision": round(precision, 3), "recall": round(recall, 3),
                "f1": round(2 * precision * recall / (precision + recall), 3) if precision + recall else 0.0}

    tune = [i for i, f in enumerate(frames) if f["video"] in TUNE]
    test = [i for i, f in enumerate(frames) if f["video"] not in TUNE]
    with_hand = lambda which: sum(bool(frames[i]["hands"]) for i in which if frames[i]["object"] is not None)  # noqa: E731
    print(f"hand finder: {hand_ms / len(frames):.0f} ms per frame on this laptop; a hand was found in "
          f"{with_hand(tune + test)} of {sum(frames[i]['object'] is not None for i in tune + test)} event frames "
          f"and {sum(bool(f['hands']) for f in frames if f['object'] is None)} of {sum(f['object'] is None for f in frames)} no-object frames")
    print(f"picked on {len(tune)} frames, reported on {len(test)} frames")
    print(f"{'where it looks':36}{'min':>5}{'crops':>7} | {'found':>9}{'false alarms':>14}{'precision':>10}{'F1':>6} | tuning F1")
    results = {}
    for look in looks:
        best = max(MINIMUMS, key=lambda m: (score(look, m, tune)["f1"], m))
        held, tuned = score(look, best, test), score(look, best, tune)
        crops = float(np.mean([len(c) for c in looks[look]]))
        results[look] = {"minimum": best, "crops_per_frame": round(crops, 2), "held_out": held, "tuning": tuned}
        print(f"{look:36}{best:>5}{crops:>7.1f} | {held['found']:>3} of {held['events']:<3}{held['false_alarms']:>6} of {held['no_object']:<5}"
              f"{held['precision']:>10.2f}{held['f1']:>6.2f} | {tuned['f1']:.2f}")

    # per object, on the held-out frames, for the best grid and the best hands setting
    print("per object on the held-out frames (found of events | times reported when it was not the labelled object):")
    for look in ("grid, 3 + 18 tiles", "grid, 18 tiles", "hands, crop 2.0 x hand", "whole frame"):
        minimum = results[look]["minimum"]
        line, table = [], {}
        for o in objects:
            its = [i for i in test if frames[i]["object"] == o]
            hit = sum(o in reported(i, looks[look][i], minimum) for i in its)
            wrong = sum(o in reported(i, looks[look][i], minimum) for i in test if frames[i]["object"] != o)
            table[o] = {"found": hit, "events": len(its), "reported_wrongly": wrong}
            line.append(f"{o[2:]} {hit}/{len(its)}|{wrong}")
        results[look]["per_object_held_out"] = table
        print(f"  {look:26} " + "  ".join(line))

    # Second view, added after the first: in these kitchens listed objects are in sight in most
    # frames whether or not they are handled, so "false alarm" above often counts a true sighting.
    # This view needs no such label. For each minimum: in how many of ALL event frames the handled
    # object was named, how many different names a frame gets on average, and what naming that
    # many of the 9 objects at random would find. "x chance" above 1 means better than guessing.
    events = [i for i, f in enumerate(frames) if f["object"] is not None]
    seen_eager = sum(bool(frames[i]["eager_hands"]) for i in events)
    print(f"eager hand finder: a hand in {seen_eager} of {len(events)} event frames")
    print(f"all {len(events)} event frames: found | names per frame | x chance, at each minimum")
    sweep = {}
    for look in looks:
        cells, sweep[look] = [], {}
        for minimum in (0.30, 0.50, 0.70, 0.90):
            found = sum(frames[i]["object"] in reported(i, looks[look][i], minimum) for i in events)
            names = float(np.mean([len(reported(i, looks[look][i], minimum)) for i in range(len(frames))]))
            lift = (found / len(events)) / (names / len(objects)) if names else 0.0
            sweep[look][str(minimum)] = {"found": found, "names_per_frame": round(names, 2), "times_chance": round(lift, 2)}
            cells.append(f"{found:>2} | {names:4.2f} | {lift:4.1f}x")
        print(f"  {look:36}" + "    ".join(cells))

    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(json.dumps({
            "data": "EPIC-KITCHENS-100, 8 videos", "objects": objects, "frames": len(frames),
            "hand_finder_ms_per_frame_laptop": round(hand_ms / len(frames), 1), "results": results, "all_events_by_minimum": sweep,
            "frame_list": [{k: f[k] for k in ("video", "t", "object", "what")} | {"hands": len(f["hands"]), "eager_hands": len(f["eager_hands"])} for f in frames],
        }, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
