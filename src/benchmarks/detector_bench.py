"""Laptop benchmark for card EYKO-9 (Option A's detector): is there a better detector than YOLOX-Tiny
under a licence we can use, and can an open-vocabulary detector name the user's own small things?
Only a winner is moved to the phone.

    task detector-bench -- run <model>     detect on both frame sets with one model, save its results
    task detector-bench -- score           one table for all models
    task detector-bench -- phone           write the inputs for the Pixel's OwlPhoneBenchmarkTest

Fixed before any model ran (14 October 2026):
  sets     ours44  the 44 frames the Pixel kept on 13 October (D:/eykon-cache/bench/vlm/frames, made by
                   `task vlm-bench -- frames`), labels docs/results/perception/presence-2026-10-13.csv
           own50   one frame every 3 s (1.5 s, 4.5 s, ...) of our own clips S1-01 and S1-02, scaled to
                   640 px on the longer side, labels docs/results/detectors/own-presence-2026-10-14.csv
                   (written by the AI assistant from contact sheets before any detector ran)
  models   yolox_tiny (the app's, Apache-2.0), rfdetr_nano (Apache-2.0): 80 COCO classes, a thing
           counts when one of its COCO classes in COCO below is reported; owlv2, omdet_turbo,
           grounding_dino (all Apache-2.0): open vocabulary, asked for the set's things with the
           phrases in QUERY below. Not tried: YOLO11 / YOLO26 / YOLOE (AGPL-3.0) and YOLO-World
           (GPL-3.0), ruled out by the project's licence rule.
           Added 14 October 2026 after the first five: owlvit (OWL-ViT base patch32, Apache-2.0) and
           owlv2_q8 (the 8-bit ONNX copy of owlv2 in OWLV2_Q8, the file a phone would load), same
           phrases, same minimum as owlv2
  minimum  each model's own documented example value, not tuned: in MIN below
  scoring  per thing: named when present (found) and named when absent (false), as in vlm_bench
  cost     ms per frame after loading, loading time and the process's peak memory, on this laptop's
           CPU (i5-13420H); not phone numbers
"""
import csv
import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import psutil

ROOT = Path("D:/eykon-cache/bench/detectors")
OUT = Path("docs/results/detectors")
SETS = {
    "ours44": (Path("D:/eykon-cache/bench/vlm/frames"), Path("docs/results/perception/presence-2026-10-13.csv")),
    "own50": (ROOT / "own", OUT / "own-presence-2026-10-14.csv"),
}
COCO = {"phone": ["cell phone"], "laptop": ["laptop"], "chair": ["chair", "couch"], "backpack": ["backpack", "handbag"],
        "car": ["car"], "monitor": ["tv"]}
QUERY = {"phone": "a phone", "laptop": "a laptop", "chair": "a chair", "backpack": "a backpack", "car": "a car",
         "monitor": "a computer monitor", "papers": "papers", "table_tennis": "a table tennis table", "keys": "keys",
         "wallet": "a wallet", "glasses": "glasses", "earbuds": "earbuds", "pen": "a pen"}
MIN = {"yolox_tiny": 0.35, "rfdetr_nano": 0.5, "owlv2": 0.1, "omdet_turbo": 0.3, "grounding_dino": 0.4,
       "owlvit": 0.1, "owlv2_q8": 0.1}
OWL = ("owlv2", "owlvit", "owlv2_q8")
OWLV2_Q8 = ("Xenova/owlv2-base-patch16-ensemble", "onnx/model_quantized.onnx")  # the 8-bit ONNX file a phone would load
FLOOR = 0.05  # OWLv2 and OmDet-Turbo keep every box above this, so `score` can also show stricter minimums
STRICTER = (0.2, 0.4, 0.5, 0.6)
HF = {"owlv2": "google/owlv2-base-patch16-ensemble", "omdet_turbo": "omlab/omdet-turbo-swin-tiny-hf",
      "grounding_dino": "IDEA-Research/grounding-dino-tiny", "owlvit": "google/owlvit-base-patch32",
      "owlv2_q8": "google/owlv2-base-patch16-ensemble"}


def labelled(set_name: str) -> tuple[list[str], list[dict]]:
    rows = list(csv.DictReader(open(SETS[set_name][1], encoding="utf-8")))
    return [c for c in rows[0] if c not in ("frame", "marked_by")], rows


def detector(name: str):
    """A function from a BGR picture and the set's things to the things it names."""
    if name == "yolox_tiny":
        import onnxruntime as ort
        from src.benchmarks.perception_golden import detect
        session = ort.InferenceSession("models/yolox_tiny.onnx", providers=["CPUExecutionProvider"])
        return lambda image, things: (coco_things({d["label"] for d in detect(session, image, MIN[name])}, things), {})
    if name == "rfdetr_nano":
        from PIL import Image
        from rfdetr import RFDETRNano
        from rfdetr.assets.coco_classes import COCO_CLASSES
        model = RFDETRNano()

        def run(image, things):
            found = model.predict(Image.fromarray(image[:, :, ::-1]), threshold=MIN[name])
            return coco_things({COCO_CLASSES[int(c)] for c in found.class_id}, things), {}
        return run
    import torch
    from PIL import Image
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
    processor = AutoProcessor.from_pretrained(HF[name])
    if name == "owlv2_q8":
        model = onnx_owlv2()
    else:
        model = AutoModelForZeroShotObjectDetection.from_pretrained(HF[name]).eval()

    def run(image, things):
        picture = Image.fromarray(image[:, :, ::-1])
        phrases = [QUERY[t] for t in things]
        if name == "grounding_dino":
            inputs = processor(images=picture, text=". ".join(phrases) + ".", return_tensors="pt")
        else:
            inputs = processor(images=picture, text=[phrases] if name in OWL else phrases, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        size = [picture.size[::-1]]
        if name in OWL:
            result = processor.post_process_grounded_object_detection(outputs, threshold=FLOOR, target_sizes=size, text_labels=[phrases])[0]
        elif name == "omdet_turbo":
            result = processor.post_process_grounded_object_detection(outputs, text_labels=phrases, threshold=FLOOR, target_sizes=size)[0]
        else:
            result = processor.post_process_grounded_object_detection(outputs, inputs.input_ids, threshold=MIN[name], text_threshold=0.3, target_sizes=size)[0]
        best = {}
        for said, conf in zip(result["text_labels"], result["scores"].tolist()):
            for t in things:
                if QUERY[t].split()[-1] in str(said):
                    best[t] = round(max(best.get(t, 0.0), conf), 3)
        return sorted(t for t, conf in best.items() if conf >= MIN[name]), best
    return run


def onnx_owlv2():
    """The 8-bit OWLv2 ONNX file behind the same call as the transformers model (processor unchanged)."""
    import onnxruntime as ort
    import torch
    from huggingface_hub import hf_hub_download
    from transformers.models.owlv2.modeling_owlv2 import Owlv2ObjectDetectionOutput
    session = ort.InferenceSession(hf_hub_download(*OWLV2_Q8), providers=["CPUExecutionProvider"])

    def model(input_ids, attention_mask, pixel_values):
        logits, boxes = session.run(["logits", "pred_boxes"], {"input_ids": input_ids.numpy(), "attention_mask": attention_mask.numpy(),
                                                               "pixel_values": pixel_values.numpy()})
        return Owlv2ObjectDetectionOutput(logits=torch.from_numpy(logits), pred_boxes=torch.from_numpy(boxes))
    return model


def coco_things(classes: set[str], things: list[str]) -> list[str]:
    return sorted(t for t in things if any(c in classes for c in COCO.get(t, [])))


def run(name: str) -> None:
    started = time.perf_counter()
    detect = detector(name)
    load_s = time.perf_counter() - started
    out = {"model": name, "min": MIN[name], "load_s": round(load_s, 1), "sets": {}}
    for set_name, (folder, _) in SETS.items():
        things, rows = labelled(set_name)
        frames = []
        for row in rows:
            image = cv2.imread(str(folder / f"{row['frame']}.jpg"))
            t = time.perf_counter()
            named, best = detect(image, things)
            frames.append({"frame": row["frame"], "named": named, "best": best, "ms": round((time.perf_counter() - t) * 1000)})
            print(set_name, row["frame"], named, frames[-1]["ms"], "ms", flush=True)
        out["sets"][set_name] = frames
    out["peak_mb"] = round(psutil.Process().memory_info().peak_wset / 2**20) if hasattr(psutil.Process().memory_info(), "peak_wset") else None
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / f"{name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


def score() -> None:
    table = {}
    for path in sorted(ROOT.glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        row = {"load_s": result["load_s"], "peak_mb": result["peak_mb"]}
        times = []
        for set_name, frames in result["sets"].items():
            things, rows = labelled(set_name)
            named = {f["frame"]: set(f["named"]) for f in frames}
            times += [f["ms"] for f in frames[1:]]
            per = {t: [sum(1 for r in rows if r[t] == "1" and t in named[r["frame"]]), sum(r[t] == "1" for r in rows),
                       sum(1 for r in rows if r[t] == "0" and t in named[r["frame"]]), sum(r[t] == "0" for r in rows)] for t in things}
            row[set_name] = {"found": sum(p[0] for p in per.values()), "present": sum(p[1] for p in per.values()),
                             "false": sum(p[2] for p in per.values()), "absent": sum(p[3] for p in per.values()), "per_thing": per}
            if any(f.get("best") for f in frames):  # stricter minimums: chosen after the first results were seen
                best = {f["frame"]: f["best"] for f in frames}
                row[set_name]["stricter"] = {m: [sum(1 for r in rows for t in things if best[r["frame"]].get(t, 0) >= m and r[t] == want)
                                                 for want in ("1", "0")] for m in STRICTER}
        row["ms_median"], row["ms_worst"] = statistics.median(times), max(times)
        table[result["model"]] = row
    print(f"{'model':16}{'ours44 found':>14}{'false':>10}{'own50 found':>14}{'false':>10}{'ms':>8}{'worst':>8}{'load s':>8}{'peak MB':>9}")
    for model, r in table.items():
        a, b = r["ours44"], r["own50"]
        print(f"{model:16}{a['found']:>8} of {a['present']:<3}{a['false']:>4} of {a['absent']:<3}{b['found']:>8} of {b['present']:<3}"
              f"{b['false']:>4} of {b['absent']:<3}{r['ms_median']:>8.0f}{r['ms_worst']:>8.0f}{r['load_s']:>8}{str(r['peak_mb']):>9}")
    for model, r in table.items():
        print(f"  {model:15}", "  ".join(f"{t} {p[0]}/{p[1]}|{p[2]}" for s in ("ours44", "own50") for t, p in r[s]["per_thing"].items()))
    print("stricter minimums (chosen after the first results were seen; found | false):")
    for model, r in table.items():
        for s in ("ours44", "own50"):
            if "stricter" in r[s]:
                print(f"  {model:15}{s:8}", "  ".join(f"{m}: {v[0]} | {v[1]}" for m, v in r[s]["stricter"].items()))
    (OUT / "scores-2026-10-14.json").write_text(json.dumps(table, indent=1), encoding="utf-8")


PHONE = ROOT / "phone"
PHONE_FRAMES = ("s1-01_016.5", "s1-01_040.5", "s1-02_025.5", "s1-02_043.5", "s1-02_061.5")  # keys, pen, glasses, all four, earbuds


def phone_inputs() -> None:
    """Inputs for OwlPhoneBenchmarkTest: the 8-bit OWLv2 file, five own frames already turned into the
    model's input (raw little-endian), the phrase tokens, and the laptop's best score per phrase to match."""
    import shutil

    import numpy as np
    from huggingface_hub import hf_hub_download
    from PIL import Image
    from transformers import AutoProcessor
    import onnxruntime as ort
    things, _ = labelled("own50")
    phrases = [QUERY[t] for t in things]
    processor = AutoProcessor.from_pretrained(HF["owlv2_q8"])
    model = hf_hub_download(*OWLV2_Q8)
    session = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    PHONE.mkdir(parents=True, exist_ok=True)
    shutil.copy(model, PHONE / "owlv2_q8.onnx")
    golden = {"phrases": phrases, "frames": {}}
    for frame in PHONE_FRAMES:
        inputs = processor(images=Image.open(SETS["own50"][0] / f"{frame}.jpg").convert("RGB"), text=[phrases], return_tensors="np")
        feed = {"input_ids": inputs["input_ids"].astype(np.int64), "attention_mask": inputs["attention_mask"].astype(np.int64),
                "pixel_values": inputs["pixel_values"].astype(np.float32)}
        feed["pixel_values"].tofile(PHONE / f"{frame}.f32")
        logits = session.run(["logits"], feed)[0][0]
        golden["frames"][frame] = [round(float(x), 4) for x in 1 / (1 + np.exp(-logits.max(0)))]
    feed["input_ids"].tofile(PHONE / "input_ids.i64")
    feed["attention_mask"].tofile(PHONE / "attention_mask.i64")
    golden["ids_shape"], golden["pixels_shape"] = list(feed["input_ids"].shape), list(feed["pixel_values"].shape)
    (PHONE / "golden.json").write_text(json.dumps(golden, indent=1), encoding="utf-8")
    print(PHONE, golden["ids_shape"], golden["pixels_shape"])


if __name__ == "__main__":
    {"run": lambda: run(sys.argv[2]), "score": score, "phone": phone_inputs}[sys.argv[1]]()
