"""YOLOE-11L (AGPL-3.0, academic use) on the phone, card EYKO-32: could it replace OWLv2 in the
"small_objects" stage? On the laptop it found 44 of 87 own things with 6 false alarms at 0.54 s per
frame (docs/results/2026-10-14-detectors-open-vocabulary.md). The laptop writes the inputs;
YoloePhoneBenchmarkTest runs the model on all 50 own frames on the Pixel; the laptop scores the
phone's answers the same way as every other model.

    task yoloe-phone -- inputs    export the model and write D:/eykon-cache/bench/detectors/yoloe_phone
    task yoloe-phone -- score     read the pulled yoloe_phone_result.json and score it

Fixed before the phone ran (15 October 2026):
  model    yoloe-11l-seg with its word list fixed to the six own50 phrases of detector_bench (QUERY),
           exported by Ultralytics to ONNX (640 x 640, opset 18). Output 0: 4 box values, one score
           per phrase, 32 mask values, for 8400 candidate boxes; the mask part is not used
  input    Ultralytics' letterbox: the frame centred on a 640 x 640 grey (114) square, RGB, 0 to 1
  scores   per thing, the highest score of its phrase over the 8400 boxes; minimum 0.25 as in the
           laptop run. The laptop's ONNX run of the same file is the reference ("laptop_onnx")
"""
import json
import sys

import numpy as np

from src.benchmarks.detector_bench import FLOOR, QUERY, ROOT, SETS, STRICTER, labelled

DIR = ROOT / "yoloe_phone"
MODEL = "yoloe-11l-seg"
MIN = 0.25
RESULT = ROOT / "yoloe_phone_result.json"


def letterbox(bgr: np.ndarray, side: int = 640) -> np.ndarray:
    import cv2
    h, w = bgr.shape[:2]
    r = min(side / h, side / w)
    nw, nh = round(w * r), round(h * r)
    image = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR) if (nw, nh) != (w, h) else bgr
    top, left = round((side - nh) / 2 - 0.1), round((side - nw) / 2 - 0.1)
    canvas = np.full((side, side, 3), 114, dtype=np.uint8)
    canvas[top:top + nh, left:left + nw] = image
    return (canvas[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255).copy()


def inputs() -> None:
    import cv2
    import onnxruntime as ort
    from ultralytics import YOLOE
    things, rows = labelled("own50")
    phrases = [QUERY[t] for t in things]
    model = YOLOE(str(ROOT / f"{MODEL}.pt"))
    model.set_classes(phrases, model.get_text_pe(phrases))
    onnx = model.export(format="onnx", imgsz=640, dynamic=False, simplify=True)
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / f"{MODEL}.onnx").write_bytes(open(onnx, "rb").read())
    session = ort.InferenceSession(str(DIR / f"{MODEL}.onnx"), providers=["CPUExecutionProvider"])
    saved = {f["frame"]: f["best"] for f in json.loads((ROOT / "yoloe_11l.json").read_text(encoding="utf-8"))["sets"]["own50"]}
    laptop, frames, diffs = {}, [], []
    for r in rows:
        x = letterbox(cv2.imread(str(SETS["own50"][0] / f"{r['frame']}.jpg")))
        x.tofile(DIR / f"{r['frame']}.f32")
        out = session.run(["output0"], {"images": x})[0][0]
        laptop[r["frame"]] = {t: round(float(out[4 + i].max()), 3) for i, t in enumerate(things)}
        diffs += [abs(laptop[r["frame"]][t] - saved[r["frame"]].get(t, 0)) for t in things if max(laptop[r["frame"]][t], saved[r["frame"]].get(t, 0)) >= FLOOR]
        frames.append(r["frame"])
    (DIR / "manifest.json").write_text(json.dumps({"file": f"{MODEL}.onnx", "frames": frames, "things": things,
                                                   "lists": {t: [i] for i, t in enumerate(things)}}), encoding="utf-8")
    (ROOT / "yoloe_phone_laptop_onnx.json").write_text(json.dumps(laptop, indent=1), encoding="utf-8")
    print(f"{len(frames)} frames; ONNX vs the laptop benchmark run: largest score difference {max(diffs):.3f}")


def found(best: dict[str, dict], minimum: float) -> tuple[int, int, dict]:
    things, rows = labelled("own50")
    per = {t: [sum(1 for r in rows if r[t] == "1" and best[r["frame"]].get(t, 0) >= minimum), sum(r[t] == "1" for r in rows),
               sum(1 for r in rows if r[t] == "0" and best[r["frame"]].get(t, 0) >= minimum)] for t in things}
    return sum(p[0] for p in per.values()), sum(p[2] for p in per.values()), per


def score() -> None:
    phone = json.loads(RESULT.read_text(encoding="utf-8"))
    laptop = json.loads((ROOT / "yoloe_phone_laptop_onnx.json").read_text(encoding="utf-8"))
    best = {f["frame"]: f["best"] for f in phone["frames"]}
    ms = [f["ms"] for f in phone["frames"]]
    diff = max(abs(best[f][t] - laptop[f][t]) for f in best for t in best[f])
    print(f"Pixel: median {np.median(ms):.0f} ms per frame (worst {max(ms):.0f}), load {phone['load_ms']:.0f} ms, "
          f"peak native heap {phone['peak_native_heap_mb']} MB; largest score difference from the laptop's ONNX run {diff:.3f}")
    for label, scores in (("Pixel", best), ("laptop ONNX", laptop)):
        hit, false, per = found(scores, MIN)
        print(f"{label:12} min {MIN}: {hit} of 87 found, {false} of 213 false   " + "  ".join(f"{t} {p[0]}/{p[1]}|{p[2]}" for t, p in per.items()))
    print("Pixel, stricter or looser minimums (chosen after the results; found | false):",
          "  ".join(f"{m}: {found(best, m)[0]} | {found(best, m)[1]}" for m in sorted({0.1, *STRICTER})))
    (ROOT / "pixel_yoloe_11l.json").write_text(json.dumps({"model": "pixel_yoloe_11l", "sets": {"own50": [
        {"frame": f, "best": b, "named": [], "ms": m} for (f, b), m in zip(best.items(), ms)]}}), encoding="utf-8")


if __name__ == "__main__":
    {"inputs": inputs, "score": score}[sys.argv[1]]()
