"""Hypothesis 8 / card EYKO-134: is YOLOX-Tiny still needed beside D-FINE S in the scene step? Laptop. Run: task yolox-beside-dfine

The scene step (OptionA.kt) runs both: YOLOX-Tiny (80 COCO names, cut-off 0.35, also COUNTS THE PEOPLE) and D-FINE S Objects365
(cut-off 0.5, its "person" left out because it called keys a person on our clips), then keeps every YOLOX detection plus each
D-FINE one that no YOLOX box of the same name overlaps > 0.5. Dropping YOLOX would save one model per kept frame.
Checked against COCO's own person-drawn boxes (instances_val2017) on the 300 COCO val photos of EYKO-121 (seed 121,
data/eyko121/coco/ids.txt), each shrunk to a 640-pixel longer side like the phone's frames, both models with the app's rules:
  objects  for each labelled non-person object: found by YOLOX (same name, IoU >= 0.5), found by D-FINE (any name, IoU >= 0.5,
           so D-FINE gets the benefit of its different name list), and found ONLY by YOLOX: what dropping YOLOX would lose;
  wrong    YOLOX boxes matching no labelled object and no D-FINE box: false finds YOLOX alone adds;
  people   the people count YOLOX gives, and what D-FINE's own "person" would give, against the labelled people.
COCO photos are not first-person video and COCO is YOLOX's own training set (an advantage for YOLOX), so a "drop it" here
would be generous to D-FINE in one way and strict in another; it is a first answer, not the gate. Writes
docs/results/yolox-beside-dfine/yolox-beside-dfine.json.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_static_int8 as ms  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/results/yolox-beside-dfine"


def main(instances):
    gt = json.loads(Path(instances).read_text())
    cats = {c["id"]: c["name"] for c in gt["categories"]}
    by_image = {}
    for a in gt["annotations"]:
        by_image.setdefault(a["image_id"], []).append(a)
    sizes = {i["id"]: (i["width"], i["height"]) for i in gt["images"]}
    chunks = re.findall(r'"([^"]+)"', (ms.APP / "java/com/eykon/memory/ml/vision/ObjectDetector.kt").read_text().split("LABELS")[1].split(")")[0])
    ylabels = [w for w in "".join(chunks).split(",") if w]
    dlabels = json.loads((ms.APP / "assets/dfine_labels.json").read_text())
    person = next(i for i, n in enumerate(dlabels) if n.lower().startswith("person"))
    yolox = ms.session(ms.MODELS / "yolox_tiny.onnx", 4, "all")
    dfine = ms.session(ms.MODELS / "dfine_s_obj365.onnx", 4, "off")
    ids = [int(x) for x in (ms.COCO / "ids.txt").read_text().split()]
    tot = dict(objects=0, yolox=0, dfine=0, either=0, only_yolox=0, yolox_wrong_alone=0, yolox_boxes=0)
    only_names, people = {}, []
    for image_id in ids:
        img = ms.frame(ms.COCO / f"{image_id:012d}.jpg")
        s = img.width / sizes[image_id][0]
        labelled = [a for a in by_image.get(image_id, []) if not a.get("iscrowd")]
        boxes = [(cats[a["category_id"]], [a["bbox"][0] * s, a["bbox"][1] * s, (a["bbox"][0] + a["bbox"][2]) * s, (a["bbox"][1] + a["bbox"][3]) * s])
                 for a in labelled]
        x, r = ms.yolox_in(img)
        yd = [(ylabels[c], conf, b) for c, conf, b in ms.yolox_decode(yolox.run(None, {"images": x})[0][0], r)]
        lo, bx = dfine.run(None, {"pixel_values": ms.dfine_in(img)})[:2]
        dd_all = ms.dfine_decode(lo[0], bx[0], img.width, img.height, -1)  # -1: keep D-FINE's person too, for the people count
        dd = [d for d in dd_all if d[0] != person]
        people.append({"labelled": sum(n == "person" for n, _ in boxes), "yolox": sum(n == "person" for n, _, _ in yd),
                       "dfine": sum(d[0] == person for d in dd_all)})
        for name, b in boxes:
            if name == "person":
                continue
            fy = any(n == name and ms.iou(b, yb) >= 0.5 for n, _, yb in yd)
            fd = any(ms.iou(b, d[2]) >= 0.5 for d in dd)
            tot["objects"] += 1
            tot["yolox"] += fy
            tot["dfine"] += fd
            tot["either"] += fy or fd
            if fy and not fd:
                tot["only_yolox"] += 1
                only_names[name] = only_names.get(name, 0) + 1
        for n, _, yb in yd:
            if n == "person":
                continue
            tot["yolox_boxes"] += 1
            if not any(ms.iou(yb, b) >= 0.5 for _, b in boxes) and not any(ms.iou(yb, d[2]) >= 0.5 for d in dd):
                tot["yolox_wrong_alone"] += 1
    err = lambda k: [abs(p[k] - p["labelled"]) for p in people]  # noqa: E731
    result = {"photos": len(ids), "objects": tot, "only_yolox_by_name": dict(sorted(only_names.items(), key=lambda kv: -kv[1])),
              "people": {"photos_with_people": sum(p["labelled"] > 0 for p in people),
                         "yolox_exact": sum(p["yolox"] == p["labelled"] for p in people),
                         "dfine_exact": sum(p["dfine"] == p["labelled"] for p in people),
                         "yolox_mean_abs_error": round(float(np.mean(err("yolox"))), 2),
                         "dfine_mean_abs_error": round(float(np.mean(err("dfine"))), 2),
                         "yolox_says_none_but_people": sum(p["yolox"] == 0 < p["labelled"] for p in people),
                         "dfine_says_none_but_people": sum(p["dfine"] == 0 < p["labelled"] for p in people)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "yolox-beside-dfine.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
