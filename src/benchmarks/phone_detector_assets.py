"""Files the app needs for the D-FINE + YOLOE step (card EYKO-32), and the laptop's answer the phone
test must match. Run: task phone-detector-assets (after task hybrid-phone -- inputs and task yoloe-phone -- inputs)

  assets/dfine_labels.json          the 366 Objects365 class names of D-FINE S, in the model's order
  assets/yoloe_words.json           the six phrases YOLOE-11L was exported with, in its class order, their
                                    plain names, and which of them the app takes from YOLOE (the rest
                                    come from D-FINE): the split measured on the Pixel
  androidTest/assets/detector_golden.jpg / .json
                                    one own frame (S1-01 at 16.5 s: keys on the desk) and what the two
                                    ONNX files the phone loads find in it on the laptop

Model files are pushed to the phone's model folder, not packaged: dfine_s_obj365.onnx
(onnx-community/dfine_s_obj365-ONNX, full precision, from D:/eykon-cache/bench/detectors/hybrid_phone) and
yoloe_11l_own.onnx (yoloe-11l-seg with the six phrases, AGPL-3.0, from D:/eykon-cache/bench/detectors/yoloe_phone).
"""
import json
import shutil
from pathlib import Path

import numpy as np

from src.benchmarks.detector_bench import QUERY, ROOT, labelled
from src.benchmarks.hybrid_phone import DIR as DFINE_DIR
from src.benchmarks.yoloe_phone import DIR as YOLOE_DIR
from src.benchmarks.yoloe_phone import MODEL as YOLOE_MODEL
from src.benchmarks.yoloe_phone import letterbox

YOLOE_USE = ["keys", "earbuds"]  # what D-FINE never named on our clips; measured split, docs/results/2026-10-14-detectors-open-vocabulary.md
ASSETS = Path("android/app/src/main/assets")
TEST_ASSETS = Path("android/app/src/androidTest/assets")
GOLDEN_FRAME = ROOT / "own" / "s1-01_016.5.jpg"


def main() -> None:
    import cv2
    import onnxruntime as ort
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForObjectDetection

    labels = AutoModelForObjectDetection.from_pretrained("ustc-community/dfine-small-obj365").config.id2label
    names = [labels[i] for i in range(len(labels))]
    (ASSETS / "dfine_labels.json").write_text(json.dumps(names) + "\n", encoding="utf-8")
    things, _ = labelled("own50")  # the order yoloe_phone exported the phrases in
    (ASSETS / "yoloe_words.json").write_text(json.dumps({"phrases": [QUERY[t] for t in things], "names": things, "use": YOLOE_USE}) + "\n", encoding="utf-8")
    (ASSETS / "owl_queries.json").unlink(missing_ok=True)

    picture = Image.open(GOLDEN_FRAME).convert("RGB")
    shutil.copy(GOLDEN_FRAME, TEST_ASSETS / "detector_golden.jpg")
    dfine = ort.InferenceSession(str(DFINE_DIR / "dfine_s_obj365.onnx"), providers=["CPUExecutionProvider"])
    pixels = AutoImageProcessor.from_pretrained("ustc-community/dfine-small-obj365")(images=picture, return_tensors="np")["pixel_values"]
    logits, boxes = dfine.run(["logits", "pred_boxes"], {"pixel_values": pixels.astype(np.float32)})
    scores = 1 / (1 + np.exp(-logits[0]))
    best_class = scores.argmax(1)
    found = [{"label": names[int(c)], "conf": round(float(scores[q, c]), 4), "box_cxcywh": [round(float(x), 4) for x in boxes[0][q]]}
             for q, c in enumerate(best_class) if scores[q, c] >= 0.3]

    yoloe = ort.InferenceSession(str(YOLOE_DIR / f"{YOLOE_MODEL}.onnx"), providers=["CPUExecutionProvider"])
    rows = yoloe.run(["output0"], {"images": letterbox(cv2.imread(str(GOLDEN_FRAME)))})[0][0]
    yoloe_best = {t: round(float(rows[4 + i].max()), 4) for i, t in enumerate(things)}
    j = int(rows[4 + things.index("keys")].argmax())
    cx, cy, w, h = (float(v) for v in rows[:4, j])
    top = round((640 - picture.size[1]) / 2 - 0.1)  # the frame is 640 wide: no resize, centred vertically
    keys_box = [round(cx - w / 2, 1), round(cy - h / 2 - top, 1), round(cx + w / 2, 1), round(cy + h / 2 - top, 1)]
    (TEST_ASSETS / "detector_golden.json").write_text(json.dumps({
        "picture": "detector_golden.jpg", "size": list(picture.size),
        "dfine": sorted(found, key=lambda d: -d["conf"]), "yoloe_best": yoloe_best, "yoloe_keys_box": keys_box,
    }, indent=1) + "\n", encoding="utf-8")
    print(len(names), "labels;", "D-FINE:", [(d["label"], d["conf"]) for d in found][:6], "YOLOE:", yoloe_best, "keys box", keys_box)


if __name__ == "__main__":
    main()
