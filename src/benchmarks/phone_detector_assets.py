"""Files the app needs for the D-FINE + OWLv2 step (card EYKO-32), and the laptop's answer the phone
test must match. Run: task phone-detector-assets

  assets/dfine_labels.json          the 366 Objects365 class names of D-FINE S, in the model's order
  assets/owl_queries.json           OWLv2's phrases as tokens (OWLv2's own tokenizer, 16 long), and the
                                    MobileCLIP-S2 vectors of the phrases that pick which frames OWLv2 sees
  androidTest/assets/detector_golden.jpg / .json
                                    one own frame (S1-01 at 16.5 s: keys on the desk) and what the two
                                    ONNX files the phone loads find in it on the laptop

Model files are pushed to the phone's model folder, not packaged: dfine_s_obj365.onnx
(onnx-community/dfine_s_obj365-ONNX, full precision) and owlv2_q8.onnx (Xenova/owlv2-base-patch16-ensemble,
8-bit), both copied to D:/eykon-cache/bench/detectors/hybrid_phone by `task hybrid-phone -- inputs`.
"""
import json
import shutil
from pathlib import Path

import numpy as np

from src.benchmarks.detector_bench import ROOT
from src.benchmarks.hybrid_phone import DIR

OWL_PHRASES = ["keys", "earbuds"]  # what D-FINE never named on our clips (docs/results/2026-10-14-detectors-open-vocabulary.md)
PICK_PHRASES = ["a photo of keys", "a photo of earbuds"]
ASSETS = Path("android/app/src/main/assets")
TEST_ASSETS = Path("android/app/src/androidTest/assets")
GOLDEN_FRAME = ROOT / "own" / "s1-01_016.5.jpg"


def main() -> None:
    import onnxruntime as ort
    import open_clip
    import torch
    from PIL import Image
    from timm.utils import reparameterize_model
    from transformers import AutoImageProcessor, AutoModelForObjectDetection, AutoProcessor

    labels = AutoModelForObjectDetection.from_pretrained("ustc-community/dfine-small-obj365").config.id2label
    names = [labels[i] for i in range(len(labels))]
    (ASSETS / "dfine_labels.json").write_text(json.dumps(names) + "\n", encoding="utf-8")

    owl = AutoProcessor.from_pretrained("google/owlv2-base-patch16-ensemble")
    tokens = owl.tokenizer(OWL_PHRASES, padding="max_length", max_length=16, return_tensors="np")
    clip, _, _ = open_clip.create_model_and_transforms("MobileCLIP-S2", pretrained="datacompdr", device="cpu")
    clip = reparameterize_model(clip.eval())
    with torch.no_grad():
        pick = torch.nn.functional.normalize(clip.encode_text(open_clip.get_tokenizer("MobileCLIP-S2")(PICK_PHRASES)), dim=-1).numpy()
    (ASSETS / "owl_queries.json").write_text(json.dumps({
        "phrases": OWL_PHRASES, "input_ids": tokens["input_ids"].tolist(), "attention_mask": tokens["attention_mask"].tolist(),
        "pick_phrases": PICK_PHRASES, "pick_vectors": [[round(float(x), 6) for x in v] for v in pick],
    }) + "\n", encoding="utf-8")

    picture = Image.open(GOLDEN_FRAME).convert("RGB")
    shutil.copy(GOLDEN_FRAME, TEST_ASSETS / "detector_golden.jpg")
    dfine = ort.InferenceSession(str(DIR / "dfine_s_obj365.onnx"), providers=["CPUExecutionProvider"])
    pixels = AutoImageProcessor.from_pretrained("ustc-community/dfine-small-obj365")(images=picture, return_tensors="np")["pixel_values"]
    logits, boxes = dfine.run(["logits", "pred_boxes"], {"pixel_values": pixels.astype(np.float32)})
    scores = 1 / (1 + np.exp(-logits[0]))
    best_class = scores.argmax(1)
    found = [{"label": names[int(c)], "conf": round(float(scores[q, c]), 4), "box_cxcywh": [round(float(x), 4) for x in boxes[0][q]]}
             for q, c in enumerate(best_class) if scores[q, c] >= 0.3]
    owl_session = ort.InferenceSession(str(DIR / "owlv2_q8.onnx"), providers=["CPUExecutionProvider"])
    owl_pixels = owl(images=picture, text=[OWL_PHRASES], return_tensors="np")["pixel_values"].astype(np.float32)
    owl_logits = owl_session.run(["logits"], {"input_ids": tokens["input_ids"].astype(np.int64),
                                              "attention_mask": tokens["attention_mask"].astype(np.int64), "pixel_values": owl_pixels})[0][0]
    owl_best = {p: round(float(1 / (1 + np.exp(-owl_logits[:, i].max()))), 4) for i, p in enumerate(OWL_PHRASES)}
    (TEST_ASSETS / "detector_golden.json").write_text(json.dumps({
        "picture": "detector_golden.jpg", "size": list(picture.size),
        "dfine": sorted(found, key=lambda d: -d["conf"]), "owl_best": owl_best,
    }, indent=1) + "\n", encoding="utf-8")
    print(len(names), "labels;", "D-FINE:", [(d["label"], d["conf"]) for d in found][:8], "OWLv2:", owl_best)


if __name__ == "__main__":
    main()
