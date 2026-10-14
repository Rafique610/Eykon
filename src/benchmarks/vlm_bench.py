"""Laptop benchmark for card EYKO-26 (Option C): which small vision-language model describes our
kept frames best, and at what cost. Only a winner is moved to the phone.

    task vlm-bench -- frames               rebuild the 44 kept frames from the clips (once)
    task vlm-bench -- run <model>          caption every frame with one model, save its results
    task vlm-bench -- score                one table for all models and Option A

Fixed before any model ran (14 October 2026):
  frames   the 44 frames the Pixel kept from the six evaluation clips on 13 October
           (docs/results/perception/pixel9proxl-2026-10-13-tiny.json), cut from the same clips
           at the same times and scaled to 640 px on the longer side, as the phone does
  prompt   PROMPT below, the same for every model that takes a prompt; greedy decoding;
           at most MAX_TOKENS new tokens
  labels   docs/results/perception/presence-2026-10-13.csv (8 things, visible or not) and
           labels-2026-10-13.csv (place), written by the AI assistant before any caption existed
  scoring  a thing counts as named when the caption contains one of its words in THINGS
           (whole words, lower case). Per thing: named when present (found) and named when absent
           (false). Place: the caption contains a word of the labelled place in PLACES; frames
           whose place is not one of those are left out of the place score.
  Option A the phone's own record for each frame (YOLOX-Tiny objects, people, place and action
           phrases), written as the app writes its caption, scored the same way
  cost     seconds per frame after loading, loading time, and the process's peak memory, on
           this laptop's CPU (i5-13420H, 15.6 GB); not phone numbers
"""
import csv
import json
import re
import statistics
import sys
import time
from pathlib import Path

import cv2
import psutil

ROOT = Path("D:/eykon-cache/bench/vlm")
FRAMES = ROOT / "frames"
PHONE = Path("docs/results/perception/pixel9proxl-2026-10-13-tiny.json")
PRESENCE = Path("docs/results/perception/presence-2026-10-13.csv")
LABELS = Path("docs/results/perception/labels-2026-10-13.csv")
CLIPS = Path("data/evals/keyframes/clips")
OUT = Path("docs/results/vlm")
PROMPT = "Describe this picture in one or two short sentences: the place, the people, and the objects you can see."
MAX_TOKENS = 80
THINGS = {
    "phone": ["phone", "phones", "smartphone", "smartphones", "mobile", "cellphone", "cell phone", "iphone"],
    "laptop": ["laptop", "laptops", "macbook", "notebook computer"],
    "chair": ["chair", "chairs", "seat", "seats", "stool", "stools"],
    "backpack": ["backpack", "backpacks", "bag", "bags", "rucksack", "schoolbag"],
    "car": ["car", "cars", "vehicle", "vehicles", "sedan"],
    "monitor": ["monitor", "monitors", "screen", "screens", "computer", "computers", "display", "displays", "tv", "television"],
    "papers": ["paper", "papers", "sheet", "sheets", "document", "documents", "notes", "worksheet", "worksheets", "booklet"],
    "table_tennis": ["table tennis", "ping pong", "ping-pong", "tennis table"],
}
PLACES = {
    "a classroom": ["classroom", "classrooms", "lecture hall", "lecture room", "class room"],
    "a hallway": ["hallway", "corridor", "hall", "lobby"],
    "a street": ["street", "road", "highway"],
}


def frames_list() -> list[dict]:
    return json.load(open(PHONE, encoding="utf-8"))["frames"]


def build_frames() -> None:
    """The phone's kept frames, cut again from the laptop's copies of the same clips."""
    FRAMES.mkdir(parents=True, exist_ok=True)
    clips = {f"clip{i}": c for i, c in enumerate(sorted(CLIPS.glob("*.mp4")), 1)}
    for f in frames_list():
        capture = cv2.VideoCapture(str(clips[f["clip"]]))
        capture.set(cv2.CAP_PROP_POS_MSEC, f["t_s"] * 1000)
        ok, image = capture.read()
        capture.release()
        assert ok, f["frame"]
        scale = 640 / max(image.shape[:2])
        if scale < 1:
            image = cv2.resize(image, (round(image.shape[1] * scale), round(image.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(FRAMES / f["frame"]), image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(len(list(FRAMES.glob("*.jpg"))), "frames in", FRAMES)


def option_a_caption(f: dict) -> str:
    """The app's caption for this frame (VideoScene.buildCaption), from the phone's own record."""
    labels = list(dict.fromkeys(o["label"] for o in sorted(f["objects"], key=lambda o: -o["conf"])))[:3]
    parts = [" and ".join(labels) if len(labels) < 3 else f"{labels[0]}, {labels[1]} and {labels[2]}"] if labels else []
    if f["people"]:
        parts.append("1 person" if f["people"] == 1 else f"{f['people']} people")
    if f["place"]:
        parts.append(f["place"] if f["place"].startswith("inside ") else f"in {f['place']}")
    if f["action"]:
        parts.append(f["action"])
    return ", ".join(parts) or "nothing recognised"


def run(model: str) -> None:
    from src.benchmarks import vlm_models

    frames = frames_list()
    process = psutil.Process()
    peak = process.memory_info().rss
    start = time.perf_counter()
    caption = vlm_models.load(model, PROMPT, MAX_TOKENS)
    load_s = time.perf_counter() - start
    rows = []
    for f in frames:
        t0 = time.perf_counter()
        text = caption(FRAMES / f["frame"])
        rows.append({"frame": f["frame"], "seconds": round(time.perf_counter() - t0, 3), "caption": text})
        peak = max(peak, process.memory_info().rss)
        print(f"{f['frame']}: {rows[-1]['seconds']:.1f} s  {text[:110]}", flush=True)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / f"{model}.json").write_text(json.dumps({"model": model, "prompt": PROMPT, "max_tokens": MAX_TOKENS, "load_s": round(load_s, 1),
                                                     "peak_memory_mb": round(peak / 1e6), "captions": rows}, indent=1), encoding="utf-8")


def named(text: str, words: list[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", low) for w in words)


def score() -> None:
    presence = {r["frame"]: r for r in csv.DictReader(open(PRESENCE, encoding="utf-8"))}
    places = {r["frame"]: r["place"] for r in csv.DictReader(open(LABELS, encoding="utf-8"))}
    results = {"option_a": {"model": "option_a", "load_s": None, "peak_memory_mb": None,
                            "captions": [{"frame": f["frame"], "seconds": f["with_saved_vector_ms"] / 1000, "caption": option_a_caption(f)} for f in frames_list()]}}
    for path in sorted(ROOT.glob("*.json")):
        results[path.stem] = json.load(open(path, encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    table, per_thing = [], {}
    for name, r in results.items():
        found = present = false = absent = place_hit = place_n = 0
        per_thing[name] = {}
        for row in r["captions"]:
            key = row["frame"][:-4]
            for thing, words in THINGS.items():
                there, said = presence[key][thing] == "1", named(row["caption"], words)
                found += there and said; present += there; false += (not there) and said; absent += not there
                cell = per_thing[name].setdefault(thing, [0, 0, 0])
                cell[0] += there and said; cell[1] += there; cell[2] += (not there) and said
            if places[key] in PLACES:
                place_n += 1
                place_hit += named(row["caption"], PLACES[places[key]])
        secs = [row["seconds"] for row in r["captions"]]
        words = statistics.median(len(row["caption"].split()) for row in r["captions"])
        table.append((name, found, present, false, absent, place_hit, place_n, statistics.median(secs), max(secs), r["load_s"], r["peak_memory_mb"], words))
    print(f"{'model':22}{'things found':>14}{'named but absent':>18}{'place':>9}{'s / frame':>11}{'worst':>7}{'load s':>8}{'peak MB':>9}{'words':>7}")
    for n, fo, pr, fa, ab, ph, pn, med, worst, load, peak, words in table:
        print(f"{n:22}{fo:>6} of {pr:<5}{fa:>8} of {ab:<7}{ph:>3} of {pn:<3}{med:>9.2f}{worst:>9.2f}{str(load):>8}{str(peak):>9}{words:>7}")
    print("per thing (found of present / named when absent):")
    for n, things in per_thing.items():
        print(f"  {n:20} " + "  ".join(f"{t} {v[0]}/{v[1]}|{v[2]}" for t, v in things.items()))
    with open(OUT / "captions-2026-10-14.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["frame", *results])
        for i, f in enumerate(frames_list()):
            writer.writerow([f["frame"], *[r["captions"][i]["caption"] for r in results.values()]])
    json.dump({"rows": [dict(zip(["model", "found", "present", "named_absent", "absent", "place_hit", "place_n", "median_s", "worst_s", "load_s", "peak_mb", "median_words"], t)) for t in table],
               "per_thing": per_thing}, open(OUT / "scores-2026-10-14.json", "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    {"frames": lambda: build_frames(), "run": lambda: run(sys.argv[2]), "score": lambda: score()}[sys.argv[1]]()
