"""Tune our keyframe layers on the tuning clips only (card EYKO-45, protocol step 5).

    task tune-keyframes -- <mobileclip onnx> <phone results json> [<cache folder>]

A laptop copy of the phone's three layers (cheap filters, hash, image-model similarity), so
thousands of threshold settings can be tried in seconds. Its agreement with the real phone run
at the phone's own thresholds is printed first; the phone stays the reference.
Held-out clips are never read here.
"""
import csv
import itertools
import json
import sys
from pathlib import Path

import cv2
import numpy as np

import keyframe_eval as ev

SMALL_SIDE, FRAME_MAX, FPS = 320, 640, 3.0
PHONE = dict(dark=25.0, bright=235.0, blur=60.0, diff=6.0, hist=0.10, hash_max=6, cos_min=0.95)


def frames_of(path: Path) -> list[np.ndarray]:
    """Frames at 3 per second, shrunk and JPEG-coded the way the phone stores them."""
    cap = cv2.VideoCapture(str(path))
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    out = []
    for i in range(int(np.ceil(duration * FPS - 1e-6))):
        cap.set(cv2.CAP_PROP_POS_MSEC, i / FPS * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        k = max(1, int(np.ceil(max(frame.shape[:2]) / FRAME_MAX)))
        frame = frame[::k, ::k][: frame.shape[0] // k // 2 * 2, : frame.shape[1] // k // 2 * 2]
        out.append(cv2.imdecode(cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])[1], cv2.IMREAD_COLOR))
    cap.release()
    return out


def small_gray(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    k = max(1, round(max(gray.shape) / SMALL_SIDE))
    h, w = gray.shape[0] // k, gray.shape[1] // k
    return cv2.resize(gray[: h * k, : w * k], (w, h), interpolation=cv2.INTER_AREA)


def dhash(gray: np.ndarray) -> int:
    tiny = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    return int("".join("1" if b else "0" for b in (tiny[:, 1:] > tiny[:, :-1]).flatten()), 2)


def embed(session, frame: np.ndarray) -> np.ndarray:
    scale = 256 / min(frame.shape[:2])
    w, h = max(256, round(frame.shape[1] * scale)), max(256, round(frame.shape[0] * scale))
    img = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)[(h - 256) // 2 : (h - 256) // 2 + 256, (w - 256) // 2 : (w - 256) // 2 + 256]
    x = np.ascontiguousarray(img[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255)
    return session.run(None, {"image": x})[0][0]


def features(path: Path, session, cache: Path) -> dict:
    """Everything the layers look at, computed once per clip and kept on disk."""
    file = cache / f"{path.stem.replace(' ', '_')}.npz"
    if file.exists():
        return dict(np.load(file))
    frames = frames_of(path)
    grays = [small_gray(f) for f in frames]
    out = dict(
        grays=np.stack(grays),
        brightness=np.array([g.mean() for g in grays]),
        blur=np.array([cv2.Laplacian(g, cv2.CV_64F).var() for g in grays]),
        hashes=np.array([dhash(g) for g in grays], dtype=np.uint64),
        vectors=np.stack([embed(session, f) for f in frames]),
    )
    np.savez_compressed(file, **out)
    return out


def ours(f: dict, p: dict) -> tuple[list[int], int]:
    """Indices of the frames our layers keep with thresholds p, and how often the image model ran."""
    kept, prev, model_calls = [], None, 0
    for i in range(len(f["blur"])):
        if f["brightness"][i] < p["dark"] or f["brightness"][i] > p["bright"] or f["blur"][i] < p["blur"]:
            continue
        g = f["grays"][i]
        if prev is not None and cv2.absdiff(f["grays"][prev], g).mean() < p["diff"] and \
                cv2.compareHist(ev_hist(f["grays"][prev]), ev_hist(g), cv2.HISTCMP_BHATTACHARYYA) < p["hist"]:
            continue
        prev = i  # the filters keep this frame; the repeat layers decide next
        if any(bin(int(f["hashes"][i]) ^ int(f["hashes"][u])).count("1") <= p["hash_max"] for u in kept):
            continue
        model_calls += 1
        if kept and max(float(f["vectors"][i] @ f["vectors"][u]) for u in kept) >= p["cos_min"]:
            continue
        kept.append(i)
    return kept, model_calls


def ev_hist(gray: np.ndarray) -> np.ndarray:
    return cv2.calcHist([gray], [0], None, [64], [0, 256])


def main(model: str, phone_json: str, cache_dir: str = "data/evals/keyframes/cache") -> None:
    import onnxruntime as ort

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    session = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    phone = {c["clip"]: c["ours"][0]["kept_times"] for c in json.loads(Path(phone_json).read_text(encoding="utf-8"))["clips"]}

    clips = sorted(ev.CLIPS.glob("*.mp4"))
    marks = {c.name: [] for c in clips}
    for row in csv.DictReader(ev.MOMENTS.open(encoding="utf-8")):
        marks[row["clip"]].append((float(row["start_s"]), float(row["end_s"])))
    tuning = [(n, c) for n, c in enumerate(clips, start=1) if n % ev.HELD_OUT_EVERY != 0]  # held-out clips are not opened

    data = {}
    for n, clip in tuning:
        duration, sharpness = ev.clip_info(clip)
        data[n] = dict(clip=clip, duration=duration, sharpness=sharpness, f=features(clip, session, cache), marks=marks[clip.name])
    minutes = sum(d["duration"] for d in data.values()) / 60
    moments = sum(len(d["marks"]) for d in data.values())

    print("## Does the laptop copy behave like the phone? (phone thresholds)\n")
    print("| Clip | Phone kept | Laptop copy kept | Same frames |")
    print("|---|---|---|---|")
    for n, d in data.items():
        mine = {round(i / FPS, 3) for i in ours(d["f"], PHONE)[0]}
        theirs = {round(t, 3) for t in phone[f"clip{n}.mp4"]}
        print(f"| {n} | {len(theirs)} | {len(mine)} | {len(mine & theirs)} |")

    def run(p: dict) -> dict:
        kept = hit = calls = 0
        for d in data.values():
            idx, c = ours(d["f"], p)
            s = ev.score([i / FPS for i in idx], d["marks"], d["sharpness"])
            kept, hit, calls = kept + s["kept"], hit + s["hit"], calls + c
        return dict(kept=kept, hit=hit, calls=calls)

    grid = dict(cos_min=[0.95, 0.92, 0.90, 0.88, 0.85, 0.82, 0.80, 0.77, 0.74, 0.70, 0.65, 0.60],
                hash_max=[6, 10, 14, 18, 22], diff=[6.0, 10.0, 15.0, 20.0, 30.0])
    results = []
    for cos_min, hash_max, diff in itertools.product(*grid.values()):
        p = PHONE | dict(cos_min=cos_min, hash_max=hash_max, diff=diff)
        results.append((p, run(p)))

    # For each number of moments found, the setting that keeps the fewest frames (then fewest model calls).
    best = {}
    for p, r in results:
        if r["hit"] not in best or (r["kept"], r["calls"]) < (best[r["hit"]][1]["kept"], best[r["hit"]][1]["calls"]):
            best[r["hit"]] = (p, r)
    print(f"\n## Ours on the tuning clips ({moments} moments, {minutes * 60:.0f} s): fewest frames for each recall\n")
    print("| Moments hit | Frames kept | Per minute | Model calls | Similarity bar | Hash bits | Change bar |")
    print("|---|---|---|---|---|---|---|")
    for hit in sorted(best, reverse=True):
        p, r = best[hit]
        print(f"| {hit} of {moments} | {r['kept']} | {r['kept'] / minutes:.1f} | {r['calls']} | {p['cos_min']} | {p['hash_max']} | {p['diff']} |")

    print("\n## The other methods at the same budgets (tuning clips; frames per clip matched to ours)\n")
    print("| Budget from ours | Ours | B0 uniform | B2 ffmpeg scene | B3 PySceneDetect content |")
    print("|---|---|---|---|---|")
    for hit in sorted(best, reverse=True)[:6]:
        p, r = best[hit]
        cells = {"uniform": [0, 0], "scene": [0, 0], "psd": [0, 0]}
        for d in data.values():
            n = max(1, len(ours(d["f"], p)[0]))
            for name, kept in (("uniform", ev.uniform(d["duration"], n)), ("scene", ev.ffmpeg_scene(d["clip"], n)), ("psd", ev.pyscenedetect(d["clip"], n, adaptive=False))):
                s = ev.score(kept, d["marks"], d["sharpness"])
                cells[name][0] += s["hit"]
                cells[name][1] += s["kept"]
        print(f"| {r['kept']} frames ({r['kept'] / minutes:.0f}/min) | {r['hit']} | " + " | ".join(f"{cells[k][0]} with {cells[k][1]}" for k in cells) + " |")
    iframes = [ev.score(ev.iframes(d["clip"]), d["marks"], d["sharpness"]) for d in data.values()]
    print(f"\nB1 codec keyframes (cannot be set to a budget): {sum(s['hit'] for s in iframes)} of {moments} with {sum(s['kept'] for s in iframes)} frames.")


if __name__ == "__main__":
    main(*sys.argv[1:])
