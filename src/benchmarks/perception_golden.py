"""Laptop reference for card EYKO-9, perception Option A. Run: task golden-perception

The product code is on the phone (android/.../ml/vision/ObjectDetector.kt, video/OptionA.kt).
This script gives the phone what it needs and what it must reproduce:

1. android/app/src/main/assets/scene_prompts.json: MobileCLIP-S2 text vectors for the place and
   action prompts in Settings. The phone has no text encoder yet, so the fixed prompts are
   embedded here once.
2. android/app/src/androidTest/assets/perception_golden.json: what the detector and the prompts
   give for the test picture on the laptop (the detector file named in Settings, YOLOX-Tiny).

The detector maths (resize with padding, decode, non-maximum suppression) follows the official
YOLOX ONNX Runtime demo, demo/ONNXRuntime/onnx_inference.py in
https://github.com/Megvii-BaseDetection/YOLOX (Apache-2.0). The test picture is that
repository's assets/dog.jpg.
"""
import json
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import open_clip
import torch
from PIL import Image
from timm.utils import reparameterize_model

from src.config import Settings

MODEL, PRETRAINED = "MobileCLIP-S2", "datacompdr"
SIDE = 416
NMS_IOU = 0.45
PICTURE = Path("android/app/src/test/resources/perception/dog.jpg")
PROMPTS_OUT = Path("android/app/src/main/assets/scene_prompts.json")
GOLDEN_OUT = Path("android/app/src/androidTest/assets/perception_golden.json")
LABELS = (  # the 80 COCO classes, in the model's order
    "person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,"
    "bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,"
    "skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,"
    "cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,"
    "potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,"
    "refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush"
).split(",")


def letterbox(image: np.ndarray) -> tuple[np.ndarray, float]:
    """Shrink to fit SIDE x SIDE, top-left, the rest grey (114). Colours stay 0 to 255, blue first."""
    ratio = min(SIDE / image.shape[0], SIDE / image.shape[1])
    resized = cv2.resize(image, (int(image.shape[1] * ratio), int(image.shape[0] * ratio)), interpolation=cv2.INTER_LINEAR)
    padded = np.full((SIDE, SIDE, 3), 114, dtype=np.uint8)
    padded[: resized.shape[0], : resized.shape[1]] = resized
    return np.ascontiguousarray(padded.transpose(2, 0, 1), dtype=np.float32), ratio


def decode(raw: np.ndarray, ratio: float, min_conf: float) -> np.ndarray:
    """Model rows to [x1, y1, x2, y2, confidence, class] in the picture's own pixels."""
    grids, strides = [], []
    for stride in (8, 16, 32):
        xs, ys = np.meshgrid(np.arange(SIDE // stride), np.arange(SIDE // stride))
        grids.append(np.stack((xs, ys), 2).reshape(-1, 2))
        strides.append(np.full((grids[-1].shape[0], 1), stride))
    grids, strides = np.concatenate(grids), np.concatenate(strides)
    centre = (raw[:, :2] + grids) * strides
    size = np.exp(raw[:, 2:4]) * strides
    scores = raw[:, 4:5] * raw[:, 5:]
    classes = scores.argmax(1)
    conf = scores[np.arange(len(classes)), classes]
    boxes = np.concatenate([centre - size / 2, centre + size / 2], 1) / ratio
    keep = conf >= min_conf
    return np.concatenate([boxes[keep], conf[keep, None], classes[keep, None]], 1)


def nms(rows: np.ndarray) -> np.ndarray:
    """Highest confidence first; a box that overlaps a kept one by more than NMS_IOU is dropped."""
    rows = rows[rows[:, 4].argsort()[::-1]]
    kept: list[np.ndarray] = []
    for row in rows:
        if all(iou(row, other) <= NMS_IOU for other in kept):
            kept.append(row)
    return np.array(kept).reshape(-1, 6)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]) + 1)
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]) + 1)
    area = lambda r: (r[2] - r[0] + 1) * (r[3] - r[1] + 1)  # noqa: E731
    return w * h / (area(a) + area(b) - w * h)


def detect(session: ort.InferenceSession, image: np.ndarray, min_conf: float) -> list[dict]:
    tensor, ratio = letterbox(image)
    raw = session.run(None, {session.get_inputs()[0].name: tensor[None]})[0][0]
    return [
        {"label": LABELS[int(r[5])], "conf": round(float(r[4]), 4), "box": [round(float(x), 1) for x in r[:4]]}
        for r in nms(decode(raw, ratio, min_conf))
    ]


def probabilities(image_vec: np.ndarray, texts: np.ndarray) -> np.ndarray:
    logits = 100 * image_vec @ texts.T
    p = np.exp(logits - logits.max())
    return p / p.sum()


def main() -> None:
    settings = Settings()
    assert len(LABELS) == 80, len(LABELS)

    session = ort.InferenceSession(str(settings.detector_model), providers=["CPUExecutionProvider"])
    detections = detect(session, cv2.imread(str(PICTURE)), settings.detector_conf)
    print(f"{PICTURE.name}:", [(d["label"], d["conf"]) for d in detections])

    model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED, device="cpu")
    model = reparameterize_model(model.eval())
    tokenizer = open_clip.get_tokenizer(MODEL)
    with torch.no_grad():
        embed = lambda prompts: torch.nn.functional.normalize(model.encode_text(tokenizer(prompts)), dim=-1).numpy()  # noqa: E731
        places, actions = embed(settings.scene_places), embed(settings.scene_actions)
        picture = preprocess(Image.open(PICTURE).convert("RGB"))[None]
        image_vec = torch.nn.functional.normalize(model.encode_image(picture), dim=-1).numpy()[0]

    vectors = lambda prompts, m: {p: [round(float(x), 6) for x in v] for p, v in zip(prompts, m)}  # noqa: E731
    PROMPTS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PROMPTS_OUT.write_text(
        json.dumps({"model": f"{MODEL}/{PRETRAINED}", "places": vectors(settings.scene_places, places),
                    "actions": vectors(settings.scene_actions, actions)}) + "\n",
        encoding="utf-8",
    )
    print(f"prompts: {PROMPTS_OUT} ({PROMPTS_OUT.stat().st_size / 1e3:.0f} KB), {len(places)} places, {len(actions)} actions")

    scene = {}
    for name, prompts, texts in (("place", settings.scene_places, places), ("action", settings.scene_actions, actions)):
        p = probabilities(image_vec, texts)
        best = int(p.argmax())
        scene[name] = prompts[best] if p[best] >= settings.scene_prompt_min else None
        scene[f"{name}_p"] = [round(float(x), 4) for x in p]
        print(f"{name}: {scene[name]}  ", {q: round(float(x), 3) for q, x in zip(prompts, p)})

    GOLDEN_OUT.write_text(
        json.dumps({"picture": PICTURE.name, "detector_conf": settings.detector_conf,
                    "prompt_min": settings.scene_prompt_min, "detections": detections, "scene": scene}, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"golden: {GOLDEN_OUT}")


if __name__ == "__main__":
    main()
