"""EYKO-121, static int8: faster with the same captions? Laptop, ONNX Runtime 1.31.1 (the app's version). Run: task model-int8

Static int8 (weights and activations, QDQ, per-channel weights) is calibrated on 50 real photos and checked on 250 others
(COCO val2017, fixed seed; data/eyko121/coco/ids.txt; never in git). Each picture is first shrunk to a 640-pixel longer
side, like the phone's frames, then prepared exactly as the app prepares it (ObjectDetector, DfineDetector, YoloeDetector,
ImageEmbedder) and decoded with the app's cut-offs (YOLOX 0.35 + NMS 0.45, D-FINE 0.5, YOLOE 0.25, place/action share 0.30).
The card's pass mark: the caption's inputs (objects, people, place, action) identical on >= 95 % of frames.
COCO is a stand-in until our own frames (own50) arrive: varied real photos, but not first-person phone video.
Writes docs/results/model-runtime/static-int8.json; int8 files go to data/eyko121/ (git-ignored).
"""

import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_runtime import session, time_it  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MODELS, WORK, OUT = ROOT / "models", ROOT / "data/eyko121", ROOT / "docs/results/model-runtime"
COCO = WORK / "coco"
APP = ROOT / "android/app/src/main"
CALIB, TEST = 50, 250


def frame(path):
    img = Image.open(path).convert("RGB")
    r = 640 / max(img.size)
    return img.resize((round(img.width * r), round(img.height * r)), Image.BILINEAR) if r < 1 else img


def yolox_in(img):  # ObjectDetector.letterbox: top-left, grey 114, BGR planes 0-255
    r = min(416 / img.height, 416 / img.width)
    small = np.asarray(img.resize((int(img.width * r), int(img.height * r)), Image.BILINEAR), dtype=np.float32)
    out = np.full((416, 416, 3), 114, np.float32)
    out[:small.shape[0], :small.shape[1]] = small
    return out[:, :, ::-1].transpose(2, 0, 1)[None].copy(), r


def dfine_in(img):  # ImagePrep.rgbPlanes(640, wholeValues): stretched, RGB / 255
    return (np.asarray(img.resize((640, 640), Image.BILINEAR), np.float32) / 255).transpose(2, 0, 1)[None].copy()


def yoloe_in(img):  # YoloeDetector.letterbox: centred, grey 114, RGB / 255
    r = min(640 / img.height, 640 / img.width)
    small = img.resize((round(img.width * r), round(img.height * r)), Image.BILINEAR)
    canvas = Image.new("RGB", (640, 640), (114, 114, 114))
    canvas.paste(small, (round((640 - small.width) / 2 - 0.1), round((640 - small.height) / 2 - 0.1)))
    return (np.asarray(canvas, np.float32) / 255).transpose(2, 0, 1)[None].copy()


def clip_in(img):  # ImageEmbedder.preprocess: shorter side 256, middle square, RGB / 255
    s = 256 / min(img.size)
    w, h = max(256, round(img.width * s)), max(256, round(img.height * s))
    big = img.resize((w, h), Image.BILINEAR)
    left, top = (w - 256) // 2, (h - 256) // 2
    return (np.asarray(big.crop((left, top, left + 256, top + 256)), np.float32) / 255).transpose(2, 0, 1)[None].copy()


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def yolox_decode(rows, ratio):  # ObjectDetector.decode + nms; label = COCO class index
    found, i = [], 0
    for stride in (8, 16, 32):
        cells = 416 // stride
        for gy in range(cells):
            for gx in range(cells):
                row = rows[i]
                i += 1
                best = 5 + int(np.argmax(row[5:]))
                conf = float(row[4] * row[best])
                if conf < 0.35:
                    continue
                cx, cy = (row[0] + gx) * stride, (row[1] + gy) * stride
                w, h = np.exp(row[2]) * stride, np.exp(row[3]) * stride
                found.append((best - 5, conf, [(cx - w / 2) / ratio, (cy - h / 2) / ratio, (cx + w / 2) / ratio, (cy + h / 2) / ratio]))
    kept = []
    for d in sorted(found, key=lambda d: -d[1]):
        if all(iou(k[2], d[2]) <= 0.45 for k in kept):
            kept.append(d)
    return kept


def dfine_decode(logits, boxes, w, h, person):  # DfineDetector.decode, its "person" left out as in OptionA
    out = []
    for q in range(logits.shape[0]):
        c = int(np.argmax(logits[q]))
        conf = 1 / (1 + np.exp(-logits[q][c]))
        if conf >= 0.5 and c != person:
            cx, cy, bw, bh = boxes[q]
            out.append((c, float(conf), [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h]))
    return sorted(out, key=lambda d: -d[1])


def same_detections(a, b):
    """Every detection has a partner with the same label and IoU >= 0.5, both ways."""
    def covered(x, y):
        return all(any(d[0] == e[0] and iou(d[2], e[2]) >= 0.5 for e in y) for d in x)
    return covered(a, b) and covered(b, a)


def best_prompt(vec, prompts):
    names, mat = list(prompts), np.array(list(prompts.values()), np.float32)
    logits = 100 * mat @ vec
    p = np.exp(logits - logits.max())
    p /= p.sum()
    k = int(np.argmax(p))
    return names[k] if p[k] >= 0.30 else None


class Reader:
    """Calibration frames for quantize_static."""

    def __init__(self, name, inputs):
        self.it = iter([{name: x} for x in inputs])

    def get_next(self):
        return next(self.it, None)


def build_int8(key, name, calib_inputs):
    from onnxruntime.quantization import QuantFormat, QuantType, quantize_static
    from onnxruntime.quantization.shape_inference import quant_pre_process
    src, pre, dst = MODELS / f"{key}.onnx", WORK / f"{key}.pre.onnx", WORK / f"{key}.int8-static.onnx"
    import onnx
    model = onnx.load(str(src))
    if max(o.version for o in model.opset_import if o.domain in ("", "ai.onnx")) < 13:  # per-channel int8 needs opset 13 (YOLOX is 11)
        from onnx import version_converter
        src = WORK / f"{key}.op13.onnx"
        onnx.save(version_converter.convert_version(model, 13), str(src))
        a = session(MODELS / f"{key}.onnx", 4, "all").run(None, {name: calib_inputs[0]})[0]
        b = session(src, 4, "all").run(None, {name: calib_inputs[0]})[0]
        print(key, "converted to opset 13; float outputs differ by at most", float(np.abs(a - b).max()), flush=True)
    try:
        quant_pre_process(str(src), str(pre), skip_symbolic_shape=True)
        model_in = pre
    except Exception as e:  # noqa: BLE001
        print(key, "pre-process skipped:", str(e)[:150], flush=True)
        model_in = src
    t = time.perf_counter()
    quantize_static(str(model_in), str(dst), Reader(name, calib_inputs), quant_format=QuantFormat.QDQ,
                    activation_type=QuantType.QUInt8, weight_type=QuantType.QInt8, per_channel=True)
    return dst, round(time.perf_counter() - t, 1)


def main():
    ids = [int(x) for x in (COCO / "ids.txt").read_text().split()]
    frames = [frame(COCO / f"{i:012d}.jpg") for i in ids]
    calib, test = frames[:CALIB], frames[CALIB:CALIB + TEST]
    chunks = re.findall(r'"([^"]+)"', (APP / "java/com/eykon/memory/ml/vision/ObjectDetector.kt").read_text().split("LABELS")[1].split(")")[0])
    labels = [w for w in "".join(chunks).split(",") if w]  # the app keeps the 80 COCO names as comma-joined strings
    dlabels = json.loads((APP / "assets/dfine_labels.json").read_text())
    person = next(i for i, n in enumerate(dlabels) if n.lower().startswith("person"))
    prompts = json.loads((APP / "assets/scene_prompts.json").read_text())
    specs = {  # key: input name, prepare, app optimisation for float
        "yolox_tiny": ("images", lambda im: yolox_in(im)[0], "all"),
        "dfine_s_obj365": ("pixel_values", dfine_in, "off"),
        "yoloe_11l_own": ("images", yoloe_in, "all"),
        "mobileclip_s2_image": ("image", clip_in, "all"),
    }
    result = {"photos": {"source": "COCO val2017, seed 121", "calibration": CALIB, "test": TEST}, "models": {}, "per_photo": []}
    sessions = {}
    for key, (name, prep, level) in specs.items():
        info = {}
        try:
            dst, secs = build_int8(key, name, [prep(im) for im in calib])
            info.update(built_s=secs, mb=round(dst.stat().st_size / 1e6, 1), float_mb=round((MODELS / f"{key}.onnx").stat().st_size / 1e6, 1))
            f_s, q_s = session(MODELS / f"{key}.onnx", 4, level), session(dst, 4, "all")
            sample = [prep(im) for im in test[:20]]
            info["float"], info["int8"] = time_it(f_s, name, sample), time_it(q_s, name, sample)
            sessions[key] = (f_s, q_s)
            if key == "dfine_s_obj365":  # control: the optimiser alone changes D-FINE's output (model_runtime.py)
                sessions["dfine_float_all"] = session(MODELS / f"{key}.onnx", 4, "all")
        except Exception as e:  # noqa: BLE001
            info["error"] = str(e)[:400]
        result["models"][key] = info
        print(key, info, flush=True)
    for n, im in enumerate(test):
        row = {"id": ids[CALIB + n]}
        cap = {}
        for variant in (0, 1):  # 0 float, 1 int8
            c = {}
            if "yolox_tiny" in sessions:
                x, r = yolox_in(im)
                c["yolox"] = yolox_decode(sessions["yolox_tiny"][variant].run(None, {"images": x})[0][0], r)
            if "dfine_s_obj365" in sessions:
                lo, bx = sessions["dfine_s_obj365"][variant].run(None, {"pixel_values": dfine_in(im)})[:2]
                c["dfine"] = dfine_decode(lo[0], bx[0], im.width, im.height, person)
            if "yoloe_11l_own" in sessions:
                o = sessions["yoloe_11l_own"][variant].run(None, {"images": yoloe_in(im)})[0][0]
                c["yoloe"] = sorted(i for i in range(6) if o[4 + i].max() >= 0.25)
            if "mobileclip_s2_image" in sessions:
                v = sessions["mobileclip_s2_image"][variant].run(None, {"image": clip_in(im)})[0][0]
                c["vec"], c["place"], c["action"] = v, best_prompt(v, prompts["places"]), best_prompt(v, prompts["actions"])
            cap[variant] = c
        a, b = cap[0], cap[1]
        if "yolox" in a:
            row["yolox_same"] = same_detections(a["yolox"], b["yolox"])
            row["people_same"] = sum(d[0] == 0 for d in a["yolox"]) == sum(d[0] == 0 for d in b["yolox"])
        if "dfine" in a:
            row["dfine_same"] = same_detections(a["dfine"], b["dfine"])
            lo, bx = sessions["dfine_float_all"].run(None, {"pixel_values": dfine_in(im)})[:2]
            f_all = dfine_decode(lo[0], bx[0], im.width, im.height, person)
            row["dfine_optimiser_only_same"] = same_detections(a["dfine"], f_all)  # float off vs float all
            row["dfine_int8_only_same"] = same_detections(f_all, b["dfine"])  # float all vs int8 (all)
        if "yoloe" in a:
            row["yoloe_same"], row["yoloe_found"] = a["yoloe"] == b["yoloe"], len(a["yoloe"])
        if "vec" in a:
            row["cosine"] = round(float(a["vec"] @ b["vec"] / (np.linalg.norm(a["vec"]) * np.linalg.norm(b["vec"]))), 5)
            row["place_same"], row["action_same"] = a["place"] == b["place"], a["action"] == b["action"]
        parts = [k for k in ("yolox_same", "people_same", "dfine_same", "place_same", "action_same") if k in row]
        row["caption_inputs_same"] = all(row[k] for k in parts)
        result["per_photo"].append(row)
        if n % 25 == 0:
            print("checked", n, flush=True)
    rows = result["per_photo"]
    summary = {k: (round(100 * sum(r[k] for r in rows if k in r) / sum(k in r for r in rows), 1) if any(k in r for r in rows) else "not run")
               for k in ("yolox_same", "people_same", "dfine_same", "dfine_optimiser_only_same", "dfine_int8_only_same", "yoloe_same",
                         "place_same", "action_same", "caption_inputs_same")}
    cos = [r["cosine"] for r in rows if "cosine" in r]
    if cos:
        summary["mobileclip_cosine"] = {"min": min(cos), "median": float(np.median(cos))}
    summary["yoloe_photos_with_a_find"] = sum(r.get("yoloe_found", 0) > 0 for r in rows)
    summary["yolox_labels"] = len(labels)
    result["summary_percent_same"] = summary
    (OUT / "static-int8.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("summary", summary)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    main()
