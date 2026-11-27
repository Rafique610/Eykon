"""EYKO-121, timing part: can the scene models run faster? Laptop. Run: task model-runtime

The five ONNX models the phone runs (models/, git-ignored; see docs/results for where each came from), timed on the repo's
golden pictures with ONNX Runtime: the app's own setting (4 threads; D-FINE with graph optimisation off, a workaround for
onnxruntime-android 1.18), thread counts, graph optimisation levels, and dynamic int8 quantisation. For int8 it also
previews how far the output moves on the golden pictures; the real quality check (captions on >= 95 % of frames) and
static int8 wait for a real frame set (own50). Speed hardly depends on what a picture shows, so these timings stand.
Writes docs/results/model-runtime/model-runtime.json; int8 files go to data/eyko121/ (git-ignored).
"""

import json
import os
import statistics
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
WORK = ROOT / "data/eyko121"
OUT = ROOT / "docs/results/model-runtime"
ASSETS = ROOT / "android/app/src/androidTest/assets"
PICTURES = [ASSETS / "detector_golden.jpg"] + sorted((ROOT / "android/app/src/test/resources/filters").glob("*.png")) \
    + [ROOT / "android/app/src/test/resources/perception/dog.jpg"]
TOKENS = ROOT / "android/app/src/test/resources/clip/tokens_golden.json"
WARMUP, RUNS = 3, 20
LEVELS = {"off": ort.GraphOptimizationLevel.ORT_DISABLE_ALL, "basic": ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
          "extended": ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED, "all": ort.GraphOptimizationLevel.ORT_ENABLE_ALL}


def square(path, side, pad=None, scale=1 / 255):
    """RGB planes 1 x 3 x side x side. pad: letterbox onto a grey square (YOLOX / YOLOE); else stretch (D-FINE, MobileCLIP)."""
    img = Image.open(path).convert("RGB")
    if pad is None:
        arr = np.asarray(img.resize((side, side), Image.BILINEAR), dtype=np.float32)
    else:
        r = min(side / img.width, side / img.height)
        small = img.resize((max(1, round(img.width * r)), max(1, round(img.height * r))), Image.BILINEAR)
        canvas = Image.new("RGB", (side, side), (pad, pad, pad))
        canvas.paste(small, ((side - small.width) // 2, (side - small.height) // 2))
        arr = np.asarray(canvas, dtype=np.float32)
    return (arr * scale).transpose(2, 0, 1)[None].copy()


def text_inputs():
    """The 10 golden sentences' token ids (tokens_golden.json), padded with 0 to the context length (77), as the phone does."""
    data = json.loads(TOKENS.read_text(encoding="utf-8"))
    n = data["context_length"]
    return [np.array([ids + [0] * (n - len(ids))], dtype=np.int64) for ids in data["sentences"].values()]


# model file, input name, the app's graph optimisation, how its inputs are made (one per golden picture or sentence)
SPECS = {
    "yolox_tiny": ("yolox_tiny.onnx", "images", "all", lambda: [square(p, 416, pad=114, scale=1.0) for p in PICTURES]),
    "dfine_s_obj365": ("dfine_s_obj365.onnx", "pixel_values", "off", lambda: [square(p, 640) for p in PICTURES]),
    "yoloe_11l_own": ("yoloe_11l_own.onnx", "images", "all", lambda: [square(p, 640, pad=114) for p in PICTURES]),
    "mobileclip_s2_image": ("mobileclip_s2_image.onnx", "image", "all", lambda: [square(p, 256) for p in PICTURES]),
    "mobileclip_s2_text": ("mobileclip_s2_text.onnx", "tokens", "all", text_inputs),
}


def session(path, threads, level):
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = threads
    opts.graph_optimization_level = LEVELS[level]
    return ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])


def time_it(sess, name, inputs):
    for i in range(WARMUP):
        sess.run(None, {name: inputs[i % len(inputs)]})
    ms = []
    for i in range(RUNS):
        t = time.perf_counter()
        sess.run(None, {name: inputs[i % len(inputs)]})
        ms.append((time.perf_counter() - t) * 1e3)
    ms.sort()
    return {"median_ms": round(statistics.median(ms), 2), "p90_ms": round(ms[int(0.9 * (len(ms) - 1))], 2)}


def outputs(sess, name, inputs):
    return [sess.run(None, {name: x}) for x in inputs]


def compare(ref, got):
    """How far the outputs moved: per output, the largest absolute change and (for vectors) the lowest cosine."""
    worst_abs, worst_cos = 0.0, 1.0
    for a_list, b_list in zip(ref, got):
        for a, b in zip(a_list, b_list):
            a, b = np.asarray(a, np.float64).ravel(), np.asarray(b, np.float64).ravel()
            worst_abs = max(worst_abs, float(np.max(np.abs(a - b))))
            if a.size <= 1024:  # embeddings: compare as vectors
                worst_cos = min(worst_cos, float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)))
    return {"max_abs_change": round(worst_abs, 5), "lowest_cosine": round(worst_cos, 5)}


def quantize(src, dst):
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(str(src), str(dst), weight_type=QuantType.QInt8)


def run_model(key):
    file, name, app_level, make = SPECS[key]
    path = MODELS / file
    inputs = make()
    res = {"file": file, "mb": round(path.stat().st_size / 1e6, 1), "input_shape": list(inputs[0].shape), "inputs": len(inputs),
           "app_setting": {"threads": 4, "optimisation": app_level}}
    ref = None
    try:
        app = session(path, 4, app_level)
        res["app"] = time_it(app, name, inputs)
        ref = outputs(app, name, inputs)
    except Exception as e:  # noqa: BLE001
        res["app"] = {"error": str(e)[:300]}
    res["threads"] = {}
    for t in (1, 2, 4, 8):
        try:
            res["threads"][t] = time_it(session(path, t, app_level), name, inputs)
        except Exception as e:  # noqa: BLE001
            res["threads"][t] = {"error": str(e)[:300]}
    res["optimisation"] = {}
    for level in LEVELS:
        try:
            s = session(path, 4, level)
            r = time_it(s, name, inputs)
            if ref is not None:
                r["vs_app_output"] = compare(ref, outputs(s, name, inputs))
            res["optimisation"][level] = r
        except Exception as e:  # noqa: BLE001
            res["optimisation"][level] = {"error": str(e)[:300]}
    q = WORK / f"{key}.int8-dynamic.onnx"
    try:
        quantize(path, q)
        s = session(q, 4, app_level)
        r = {"mb": round(q.stat().st_size / 1e6, 1), **time_it(s, name, inputs)}
        if ref is not None:
            r["preview_vs_float"] = compare(ref, outputs(s, name, inputs))
        res["int8_dynamic"] = r
    except Exception as e:  # noqa: BLE001
        res["int8_dynamic"] = {"error": str(e)[:300]}
    print(key, json.dumps(res)[:600], flush=True)
    return res


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    import platform
    result = {"onnxruntime": ort.__version__, "cpu": platform.processor() or platform.machine(), "cores": os.cpu_count(),
              "pictures": [str(p.relative_to(ROOT)) for p in PICTURES], "warmup": WARMUP, "runs": RUNS,
              "models": {key: run_model(key) for key in SPECS}}
    (OUT / "model-runtime.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("wrote docs/results/model-runtime/model-runtime.json")
