"""Hypothesis 1 (decision re-check, 26 Nov): does dropping repeats against the WHOLE video lose "it was still there"?

    task dedup-window -- <clip.mp4> [<clip.mp4> ...]

The app's dedup stage (VideoDedup.kt) drops a frame whose hash is within 6 bits, or whose MobileCLIP vector is within
cosine 0.95, of ANY unique frame kept so far in the video. The worry: for "where are my keys now", coming back to the same
view later is the evidence that the keys were still there, and that frame is dropped. The alternative compares only with
unique frames kept in the last W seconds.

The laptop copy of the phone's layers (keyframe_tune.py: 3 frames a second, cheap filters, hash, MobileCLIP) is run with
  whole   the app's rule (compare with every unique frame so far),
  W s     compare only with unique frames from the last W seconds,
  none    no dedup at all (the reference: every frame the filters keep).
Every frame the filters keep is then run through the app's two object models with the app's rules (model_static_int8.py:
D-FINE S Objects365 at 0.5 with "person" left out, YOLOE-11L with the app's six own phrases at 0.25), so each variant's
kept frames have the same detections. For each object name it reports when the variant last saw it against the
reference, and how many frames each variant keeps (each kept frame costs the scene, small_objects and latest stages).
Writes docs/results/dedup-window/dedup-window.json. Frames and clips are not saved.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keyframe_tune as kt  # noqa: E402
import model_static_int8 as ms  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/results/dedup-window"
WINDOWS = (10, 20, 30)
WORDS = json.loads((ROOT / "android/app/src/main/assets/yoloe_words.json").read_text())  # the app's six phrases; it keeps "use" only
OWN = WORDS["names"]


def filtered(f, p):
    """Indices the cheap filters keep (the same loop as keyframe_tune.ours, before the repeat layers)."""
    out, prev = [], None
    for i in range(len(f["blur"])):
        if f["brightness"][i] < p["dark"] or f["brightness"][i] > p["bright"] or f["blur"][i] < p["blur"]:
            continue
        g = f["grays"][i]
        if prev is not None and cv2.absdiff(f["grays"][prev], g).mean() < p["diff"] and \
                cv2.compareHist(kt.ev_hist(f["grays"][prev]), kt.ev_hist(g), cv2.HISTCMP_BHATTACHARYYA) < p["hist"]:
            continue
        prev = i
        out.append(i)
    return out


def dedup(f, cand, p, window):
    """The app's two repeat layers over the filtered frames; window=None compares with every kept frame (the app)."""
    kept = []
    for i in cand:
        t = i / kt.FPS
        pool = kept if window is None else [u for u in kept if t - u / kt.FPS <= window]
        if any(bin(int(f["hashes"][i]) ^ int(f["hashes"][u])).count("1") <= p["hash_max"] for u in pool):
            continue
        if pool and max(float(f["vectors"][i] @ f["vectors"][u]) for u in pool) >= p["cos_min"]:
            continue
        kept.append(i)
    return kept


def main(clips):
    sess = lambda name, level: ms.session(ROOT / "models" / name, 4, level)  # noqa: E731
    clip = sess("mobileclip_s2_image.onnx", "all")
    dfine = sess("dfine_s_obj365.onnx", "off")
    yoloe = sess("yoloe_11l_own.onnx", "all")
    dlabels = json.loads((ms.APP / "assets/dfine_labels.json").read_text())
    person = next(i for i, n in enumerate(dlabels) if n.lower().startswith("person"))
    result = {"rule": "app thresholds: " + json.dumps(kt.PHONE), "windows_s": WINDOWS, "clips": {}}
    for path in map(Path, clips):
        frames = kt.frames_of(path)
        grays = [kt.small_gray(x) for x in frames]
        f = dict(grays=np.stack(grays), brightness=np.array([g.mean() for g in grays]),
                 blur=np.array([cv2.Laplacian(g, cv2.CV_64F).var() for g in grays]),
                 hashes=np.array([kt.dhash(g) for g in grays], dtype=np.uint64),
                 vectors=np.stack([kt.embed(clip, x) for x in frames]))
        cand = filtered(f, kt.PHONE)
        labels = {}
        for i in cand:  # detections once per filtered frame, shared by every variant
            im = Image.fromarray(frames[i][:, :, ::-1])
            lo, bx = dfine.run(None, {"pixel_values": ms.dfine_in(im)})[:2]
            names = {dlabels[d[0]] for d in ms.dfine_decode(lo[0], bx[0], im.width, im.height, person)}
            o = yoloe.run(None, {"images": ms.yoloe_in(im)})[0][0]
            names |= {f"own:{OWN[k]}" for k in range(6) if OWN[k] in WORDS["use"] and o[4 + k].max() >= 0.25}
            labels[i] = sorted(names)
        variants = {"none": cand, "whole": dedup(f, cand, kt.PHONE, None)} | {f"{w} s": dedup(f, cand, kt.PHONE, w) for w in WINDOWS}
        every = sorted({n for i in cand for n in labels[i]})
        last = {v: {n: max((i / kt.FPS for i in idx if n in labels[i]), default=None) for n in every} for v, idx in variants.items()}
        seen = {v: {n: sum(n in labels[i] for i in idx) for n in every} for v, idx in variants.items()}
        report = {"frames": len(frames), "filtered": len(cand), "kept": {v: len(idx) for v, idx in variants.items()}, "objects": {}}
        for n in every:
            report["objects"][n] = {v: {"last_seen_s": None if last[v][n] is None else round(last[v][n], 1), "frames": seen[v][n]} for v in variants}
        # how far behind the reference each variant's "last seen" is, over all object names
        for v in variants:
            lags = [last["none"][n] - (last[v][n] if last[v][n] is not None else 0.0) for n in every]
            report.setdefault("lag_s", {})[v] = {"median": round(float(np.median(lags)), 1), "max": round(float(max(lags)), 1),
                                                 "names_exact": sum(x == 0 for x in lags), "names": len(every),
                                                 "names_lost": sum(last[v][n] is None for n in every)}
        result["clips"][path.name] = report
        print(path.name, json.dumps({k: report[k] for k in ("frames", "filtered", "kept", "lag_s")}), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dedup-window.json").write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
