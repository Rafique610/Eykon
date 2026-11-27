"""Hypothesis 9b (decision re-check, 26 Nov; card EYKO-138): can one cut-off on the best score tell "it is in my videos"
from "it is in none of them"? Today the search always returns 20 hits, even for a thing never filmed. Laptop. Run:

    task not-found-cutoff -- <instances_val2017.json>

Photos: the 300 COCO val photos of EYKO-121 (seed 121), embedded with the app's MobileCLIP-S2 image model and its preparation
(shorter side 256, middle square). Phrases: each COCO object name as typed ("dog", "cell phone"), through the app's text model.
For every name that is in at least one photo (by COCO's person-drawn labels):
  present  the best score over all 300 photos;
  absent   the best score after taking out every photo that has the name: the same question asked of a library without it.
Two kinds of cut-off: a fixed score, and a relative one (how many standard deviations the best score stands above that
phrase's usual score in the same library). If one separates the two lists, the app can answer "not seen" honestly. Reported: how well they separate (AUC),
and at the cut-off with the fewest mistakes, how many "present" it would hide and how many "absent" it would still answer.
COCO photos are not first-person frames; a first answer, the real check is on own clips (EYKO-138).
Writes docs/results/not-found/not-found.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import open_clip

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_static_int8 as ms  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/results/not-found"


def main(instances):
    gt = json.loads(Path(instances).read_text())
    cats = {c["id"]: c["name"] for c in gt["categories"]}
    ids = [int(x) for x in (ms.COCO / "ids.txt").read_text().split()]
    has = {i: set() for i in ids}
    for a in gt["annotations"]:
        if a["image_id"] in has:
            has[a["image_id"]].add(cats[a["category_id"]])
    image = ms.session(ms.MODELS / "mobileclip_s2_image.onnx", 4, "all")
    vecs = np.vstack([image.run(None, {"image": ms.clip_in(ms.frame(ms.COCO / f"{i:012d}.jpg"))})[0][0] for i in ids])
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    tok = open_clip.get_tokenizer("MobileCLIP-S2")
    text = ort.InferenceSession(str(ms.MODELS / "mobileclip_s2_text.onnx"), providers=["CPUExecutionProvider"])
    rows = []
    for name in sorted(set(cats.values())):
        inside = np.array([name in has[i] for i in ids])
        if not inside.any() or inside.all():
            continue
        q = text.run(None, {"tokens": tok([name]).numpy().astype(np.int64)})[0][0]
        s = vecs @ (q / np.linalg.norm(q))
        a = s[~inside]  # the library without it
        rows.append({"name": name, "photos_with_it": int(inside.sum()), "present": float(s.max()), "absent": float(a.max()),
                     # relative: how far the best score stands above that phrase's usual score in the same library (z-score)
                     "present_z": float((s.max() - s.mean()) / s.std()), "absent_z": float((a.max() - a.mean()) / a.std()),
                     "best_photo_has_it": bool(inside[int(np.argmax(s))])})
    def separation(key):
        pres = np.array([r[f"present{key}"] for r in rows])
        absn = np.array([r[f"absent{key}"] for r in rows])
        auc = float(np.mean([(p > a) + 0.5 * (p == a) for p in pres for a in absn]))
        best_err, best_cut = min((int((pres < c).sum()) + int((absn >= c).sum()), float(c)) for c in np.unique(np.concatenate([pres, absn])))
        return {"auc_present_vs_absent": round(auc, 3), "best_cutoff": round(best_cut, 4), "mistakes_at_best": best_err,
                "of": 2 * len(rows), "present_hidden_at_best": int((pres < best_cut).sum()),
                "absent_still_answered_at_best": int((absn >= best_cut).sum()),
                "present_median": round(float(np.median(pres)), 4), "absent_median": round(float(np.median(absn)), 4)}
    result = {"photos": len(ids), "names": len(rows), "fixed_score_cutoff": separation(""), "relative_z_cutoff": separation("_z"),
              "top1_has_it_when_present": sum(r["best_photo_has_it"] for r in rows), "per_name": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "not-found.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_name"}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
