"""The mixed detectors of detector_hybrid, measured on the phone (card EYKO-32). The laptop writes the
inputs; HybridPhoneBenchmarkTest runs D-FINE S (Objects365, full precision ONNX) and OWLv2 (8-bit ONNX)
on all 50 own frames on the Pixel; the laptop turns the phone's answers into detector_bench results
and scores every way of picking frames with detector_hybrid.

    task hybrid-phone -- inputs     write D:/eykon-cache/bench/detectors/hybrid_phone (about 800 MB)
    task hybrid-phone -- score      read the pulled hybrid_phone_result.json, score like the laptop

Fixed before the phone ran (15 October 2026):
  inputs   the processors detector_bench used (D-FINE: 640 x 640; OWLv2: 960 x 960), so the phone gets
           exactly the laptop's pixels; only the model runs are timed on the phone
  scores   per thing: the highest sigmoid score over the model's 300 (D-FINE) or 3600 (OWLv2) boxes of
           any class or phrase listed for it. The laptop's ONNX run of the same files gives the
           reference the phone is compared with ("laptop_onnx")
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np

from src.benchmarks.detector_bench import OWLV2_Q8, QUERY, ROOT, SETS, VOCAB, labelled

DIR = ROOT / "hybrid_phone"
DFINE_ONNX = ("onnx-community/dfine_s_obj365-ONNX", "onnx/model.onnx")
RESULT = ROOT / "hybrid_phone_result.json"


def best_per_thing(logits: np.ndarray, lists: dict[str, list[int]]) -> dict[str, float]:
    scores = 1 / (1 + np.exp(-logits))
    return {t: round(float(scores[:, idx].max()), 3) for t, idx in lists.items() if idx}


def inputs() -> None:
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForObjectDetection, AutoProcessor
    things, rows = labelled("own50")
    names = AutoModelForObjectDetection.from_pretrained("ustc-community/dfine-small-obj365").config.id2label
    dfine_lists = {t: [i for i, n in names.items() if n in VOCAB["o365"].get(t, [])] for t in things}
    phrases = [QUERY[t] for t in things]
    owl_lists = {t: [i] for i, t in enumerate(things)}
    dfine_proc = AutoImageProcessor.from_pretrained("ustc-community/dfine-small-obj365")
    owl_proc = AutoProcessor.from_pretrained("google/owlv2-base-patch16-ensemble")
    models = {"dfine": hf_hub_download(*DFINE_ONNX), "owl": hf_hub_download(*OWLV2_Q8)}
    sessions = {k: ort.InferenceSession(v, providers=["CPUExecutionProvider"]) for k, v in models.items()}
    DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(models["dfine"], DIR / "dfine_s_obj365.onnx")
    shutil.copy(models["owl"], DIR / "owlv2_q8.onnx")
    frames, laptop = [], {"dfine": {}, "owl": {}}
    for r in rows:
        picture = Image.open(SETS["own50"][0] / f"{r['frame']}.jpg").convert("RGB")
        d = dfine_proc(images=picture, return_tensors="np")["pixel_values"].astype(np.float32)
        o = owl_proc(images=picture, text=[phrases], return_tensors="np")
        d.tofile(DIR / f"{r['frame']}.dfine.f32")
        o["pixel_values"].astype(np.float32).tofile(DIR / f"{r['frame']}.owl.f32")
        ids, mask = o["input_ids"].astype(np.int64), o["attention_mask"].astype(np.int64)
        laptop["dfine"][r["frame"]] = best_per_thing(sessions["dfine"].run(["logits"], {"pixel_values": d})[0][0], dfine_lists)
        laptop["owl"][r["frame"]] = best_per_thing(sessions["owl"].run(["logits"], {"input_ids": ids, "attention_mask": mask,
                                                                                      "pixel_values": o["pixel_values"].astype(np.float32)})[0][0], owl_lists)
        frames.append(r["frame"])
        print(r["frame"], laptop["dfine"][r["frame"]], laptop["owl"][r["frame"]], flush=True)
    ids.tofile(DIR / "input_ids.i64")
    mask.tofile(DIR / "attention_mask.i64")
    manifest = {"frames": frames, "things": things,
                "dfine": {"file": "dfine_s_obj365.onnx", "shape": list(d.shape), "lists": dfine_lists},
                "owl": {"file": "owlv2_q8.onnx", "shape": list(o["pixel_values"].shape), "ids_shape": list(ids.shape), "lists": owl_lists}}
    (DIR / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (ROOT / "hybrid_phone_laptop_onnx.json").write_text(json.dumps(laptop, indent=1), encoding="utf-8")


def score() -> None:
    from src.benchmarks import detector_hybrid
    phone = json.loads(RESULT.read_text(encoding="utf-8"))
    laptop = json.loads((ROOT / "hybrid_phone_laptop_onnx.json").read_text(encoding="utf-8"))
    medians = {}
    for model, name in (("dfine", "pixel_dfine_s_obj365"), ("owl", "pixel_owlv2_q8")):
        frames = [{"frame": f["frame"], "best": f[model], "named": [], "ms": f[f"{model}_ms"]} for f in phone["frames"]]
        diff = max(abs(f[model].get(t, 0) - laptop[model][f["frame"]].get(t, 0)) for f in phone["frames"] for t in f[model])
        medians[model] = float(np.median([f["ms"] for f in frames])) / 1000
        print(f"{model}: Pixel median {np.median([f['ms'] for f in frames]):.0f} ms per frame, load {phone[f'{model}_load_ms']:.0f} ms, "
              f"largest score difference from the laptop's ONNX run {diff:.3f}")
        (ROOT / f"{name}.json").write_text(json.dumps({"model": name, "sets": {"own50": frames}}), encoding="utf-8")
    print(f"peak native heap {phone['peak_native_heap_mb']} MB on {phone['device']}")
    detector_hybrid.main(dfine="pixel_dfine_s_obj365", owl="pixel_owlv2_q8", sets=("own50",), owl_mins=(0.1, 0.2, 0.3, 0.4),
                         out="hybrid-pixel-2026-10-15.json", owl_s=medians["owl"])
    print(f"D-FINE on every kept frame: about {medians['dfine'] * detector_hybrid.KEPT_PER_CLIP:.0f} s per 75 s clip on the Pixel")


if __name__ == "__main__":
    {"inputs": inputs, "score": score}[sys.argv[1]]()
