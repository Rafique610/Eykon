"""EYKO-64: what does YOLOE-11S prompt-free (AGPL-3.0, academic use only) cost on the Pixel?

EYKO-62 found that crops of any object (this model's 10 surest boxes of at least 0.10 per frame, then a MobileCLIP vector
per crop) lift last-seen answers by 11 points on held-out set B, but it has no phone cost. The laptop writes the model and
the kept frames of the two kit clips; YoloePfPhoneBenchmarkTest times it on the Pixel; the laptop reads the answer.

    uv run --with ultralytics --with onnx --with onnxslim --with onnxruntime python -m src.benchmarks.yoloe_pf_phone inputs
    uv run --with numpy python -m src.benchmarks.yoloe_pf_phone score <pulled yoloe_pf_phone_result.json>

Inputs: the kept frames pulled from the Pixel into D:/eykon-cache/bench/detectors/yoloe_pf_frames/clip1 and clip2
(26 frames: 10 and 16). Each is letterboxed to 640 x 640 exactly as yoloe_phone.py does (grey 114, RGB, 0 to 1).
The model is the Ultralytics export to ONNX (640, opset default, simplified); it has no word list to fix.
"""
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("D:/eykon-cache/bench/detectors")
FRAMES = ROOT / "yoloe_pf_frames"
DIR = ROOT / "yoloe_pf_phone"
MODEL = "yoloe-11s-seg-pf"
BOXES, MINIMUM = 10, 0.10  # EYKO-62: the 10 surest boxes of at least 0.10 per frame


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


def top_boxes(out: np.ndarray) -> tuple[int, int, float]:
    """out: (4 + classes + 32 mask values, 8400 boxes). The best class score of every box, then the 10 surest at or above 0.10."""
    classes = out.shape[0] - 4 - 32
    best = out[4:4 + classes].max(axis=0)
    top = np.argsort(-best)[:BOXES]
    return int((best >= MINIMUM).sum()), int((best[top] >= MINIMUM).sum()), float(best.max())


def inputs() -> None:
    import cv2
    import onnxruntime as ort
    from ultralytics import YOLOE
    DIR.mkdir(parents=True, exist_ok=True)
    onnx = YOLOE(str(ROOT / f"{MODEL}.pt")).export(format="onnx", imgsz=640, dynamic=False, simplify=True)
    target = DIR / f"{MODEL}.onnx"
    shutil.copy(onnx, target)
    session = ort.InferenceSession(str(target), providers=["CPUExecutionProvider"])
    print("model:", target.name, f"{target.stat().st_size / 1e6:.1f} MB; outputs:", [(o.name, o.shape) for o in session.get_outputs()])
    frames, laptop = [], {}
    for clip in ("clip1", "clip2"):
        for jpg in sorted((FRAMES / clip).glob("*.jpg")):
            name = f"{clip}_{jpg.stem}"
            x = letterbox(cv2.imread(str(jpg)))
            x.tofile(DIR / f"{name}.f32")
            start = time.perf_counter()
            out = session.run(["output0"], {"images": x})[0][0]
            ms = (time.perf_counter() - start) * 1000
            above, kept, best = top_boxes(out)
            laptop[name] = {"boxes_at_least_min": above, "crops": kept, "best_score": round(best, 3), "ms": round(ms)}
            frames.append(name)
    (DIR / "manifest.json").write_text(json.dumps({"file": target.name, "frames": frames, "boxes": BOXES, "minimum": MINIMUM}), encoding="utf-8")
    (ROOT / "yoloe_pf_phone_laptop_onnx.json").write_text(json.dumps(laptop, indent=1), encoding="utf-8")
    crops = [v["crops"] for v in laptop.values()]
    print(f"{len(frames)} frames; crops per frame (10 surest, at least {MINIMUM}): median {np.median(crops):.0f}, mean {np.mean(crops):.1f}, "
          f"total {sum(crops)}; laptop ONNX run: median {np.median([v['ms'] for v in laptop.values()]):.0f} ms per frame")


def score(result: Path) -> None:
    phone = json.loads(result.read_text(encoding="utf-8"))
    laptop = json.loads((ROOT / "yoloe_pf_phone_laptop_onnx.json").read_text(encoding="utf-8"))
    run = [f["run_ms"] for f in phone["frames"]]
    post = [f["post_ms"] for f in phone["frames"]]
    same = sum(1 for f in phone["frames"] if f["crops"] == laptop[f["frame"]]["crops"])
    print(f"Pixel: model run median {np.median(run):.0f} ms per frame (worst {max(run)}), pick-the-10-boxes median {np.median(post):.0f} ms, "
          f"load {phone['load_ms']:.0f} ms, peak native heap {phone['peak_native_heap_mb']} MB, peak PSS {phone['peak_pss_mb']} MB")
    print(f"crops per frame equal to the laptop's ONNX run on {same} of {len(phone['frames'])} frames")


if __name__ == "__main__":
    inputs() if sys.argv[1] == "inputs" else score(Path(sys.argv[2]))
