"""EYKO-120: where the `latest` stage spends its time, and faster versions with the same output. Run: task latest-profile

The phone's VideoLatest.kt is ported here line by line ("now") next to the faster version ("new"), and both run on real data:
  1 crop cut     decode the frame once per box (now) or once per frame (new); the real 640x360 test frame and its 12 D-FINE boxes.
                 Pass mark: every crop is the same pixels.
  2 crop vector  MobileCLIP-S2 through ONNX Runtime with 4 threads (as the phone): one crop per run (now) or the frame's crops
                 in one batch (new). Reports how far the vectors move and how many real crop pairs sit that close to 0.87.
  3 relink       the current loop, or one cosine per pair and only changed rows written (new), on the 90 real object crops the
                 Pixel saved for EYKO-15, then on a growing library of real MobileCLIP vectors (COCO). Pass mark: the same links.
The ONNX file is exported from the cached weights into data/eyko120/ (git-ignored; Apple research-only licence).
"""
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FRAME = ROOT / "android/app/src/androidTest/assets/detector_golden.jpg"
BOXES = ROOT / "android/app/src/androidTest/assets/detector_golden.json"
EXTRA = sorted((ROOT / "android/app/src/test/resources/filters").glob("*.png")) + [ROOT / "android/app/src/test/resources/perception/dog.jpg"]
CROPS = ROOT / "docs/results/latest/pixel9proxl-object-crops-2026-10-13.json"
COCO = ROOT / "data/eyko91_coco/images_512.f32"
MODEL = ROOT / "data/eyko120/mobileclip_s2_image_batch.onnx"
OUT = ROOT / "docs/results/latest-profile"
MIN_BOX_SIDE, CROP_COSINE_MIN, SIDE = 16, 0.87, 256


def crop_square(box, width, height):
    """VideoLatest.cropSquare: the square around a box, inside the picture; None when the box is too small."""
    left, top = max(0.0, box[0]), max(0.0, box[1])
    right, bottom = min(float(width), box[2]), min(float(height), box[3])
    if right - left < MIN_BOX_SIDE or bottom - top < MIN_BOX_SIDE:
        return None
    side = min(round(max(right - left, bottom - top)), min(width, height))
    x = min(max(round((left + right) / 2 - side / 2), 0), width - side)
    y = min(max(round((top + bottom) / 2 - side / 2), 0), height - side)
    return x, y, side


def frame_boxes():
    spec = json.loads(BOXES.read_text(encoding="utf-8"))
    w, h = spec["size"]
    return [[(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h] for cx, cy, bw, bh in (d["box_cxcywh"] for d in spec["dfine"])]


def cut_now(path, boxes):
    out = []
    for box in boxes:
        with Image.open(path) as picture:  # one decode per box, as cropVector does
            picture.load()
            sq = crop_square(box, *picture.size)
            out.append(None if sq is None else picture.crop((sq[0], sq[1], sq[0] + sq[2], sq[1] + sq[2])))
    return out


def cut_new(path, boxes):
    with Image.open(path) as picture:  # one decode per frame
        picture.load()
        squares = [crop_square(b, *picture.size) for b in boxes]
        return [None if s is None else picture.crop((s[0], s[1], s[0] + s[2], s[1] + s[2])) for s in squares]


def median_ms(fn, repeats):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times)


def part1():
    boxes = frame_boxes()
    a, b = cut_now(FRAME, boxes), cut_new(FRAME, boxes)
    same = all((x is None and y is None) or (x is not None and y is not None and x.tobytes() == y.tobytes()) for x, y in zip(a, b))
    now, new = median_ms(lambda: cut_now(FRAME, boxes), 200), median_ms(lambda: cut_new(FRAME, boxes), 200)
    crops = [c for c in b if c is not None]
    print(f"1 crop cut: {len(boxes)} boxes, {len(crops)} crops; now {now:.2f} ms, new {new:.2f} ms per frame; same pixels: {same}")
    return {"boxes": len(boxes), "crops": len(crops), "now_ms": now, "new_ms": new, "same_pixels": same}, crops


def preprocess(picture):
    """ImageEmbedder.preprocess: shorter side to 256 (bilinear), the middle 256 x 256, 0 to 1, RGB planes."""
    picture = picture.convert("RGB")
    scale = SIDE / min(picture.size)
    w, h = max(SIDE, round(picture.width * scale)), max(SIDE, round(picture.height * scale))
    scaled = picture.resize((w, h), Image.BILINEAR)
    left, top = (w - SIDE) // 2, (h - SIDE) // 2
    return np.asarray(scaled.crop((left, top, left + SIDE, top + SIDE)), dtype=np.float32).transpose(2, 0, 1) / 255.0


def export_model():
    """The phone's export (export_clip.py) with a batch axis that may vary; same weights, same layers."""
    if MODEL.exists():
        return
    import open_clip
    import torch
    from timm.utils import reparameterize_model

    model, _, _ = open_clip.create_model_and_transforms("MobileCLIP-S2", pretrained="datacompdr", device="cpu")
    model = reparameterize_model(model.eval()).eval()

    class Encoder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = model

        def forward(self, image):
            return torch.nn.functional.normalize(self.model.encode_image(image), dim=-1)

    MODEL.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(Encoder().eval(), torch.zeros(1, 3, SIDE, SIDE), str(MODEL), input_names=["image"], output_names=["embedding"],
                      opset_version=17, dynamo=False, dynamic_axes={"image": {0: "n"}, "embedding": {0: "n"}})


def part2(crops):
    import onnxruntime as ort

    export_model()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4  # as the phone
    session = ort.InferenceSession(str(MODEL), options, providers=["CPUExecutionProvider"])
    pictures = crops + [Image.open(p) for p in EXTRA]
    batch = np.stack([preprocess(p) for p in pictures])
    run = lambda x: session.run(None, {"image": x})[0]
    run(batch[:1]); run(batch)  # warm up
    single = np.concatenate([run(batch[i:i + 1]) for i in range(len(batch))])
    together = run(batch)
    rows = {}
    for n in (1, 4, 8, len(crops)):
        part = batch[:n]
        one = median_ms(lambda: [run(part[i:i + 1]) for i in range(n)], 15) / n
        many = median_ms(lambda: run(part), 15) / n
        rows[n] = {"one_at_a_time_ms": one, "batch_ms": many}
        print(f"2 crop vector, {n:2} crops: one at a time {one:.1f} ms per crop, batch {many:.1f} ms per crop ({one / many:.2f}x)")
    max_abs = float(np.abs(single - together).max())
    cos_single, cos_batch = single @ single.T, together @ together.T
    max_dcos = float(np.abs(cos_single - cos_batch).max())
    real = np.array([c["vector"] for c in json.loads(CROPS.read_text(encoding="utf-8"))["crops"]], dtype=np.float32)
    labels = [c["label"] for c in json.loads(CROPS.read_text(encoding="utf-8"))["crops"]]
    pair_cos = [float(real[i] @ real[j]) for i in range(len(real)) for j in range(i + 1, len(real)) if labels[i] == labels[j]]
    near = sum(abs(c - CROP_COSINE_MIN) <= max_dcos for c in pair_cos)
    print(f"2 batch against one at a time: largest vector change {max_abs:.2e}, largest cosine change {max_dcos:.2e}; "
          f"{near} of {len(pair_cos)} real same-label pairs are that close to {CROP_COSINE_MIN}")
    return {"by_batch_size": rows, "max_abs_change": max_abs, "max_cosine_change": max_dcos, "real_pairs": len(pair_cos), "pairs_that_close": near}


def relink_now(rows, t, dot):
    """VideoLatest.relink: rows (id, frame, vector) in time order -> superseded_by per id, plus the work done."""
    latest, sup, cosines = [], {}, 0
    for row in rows:
        candidates = [r for r in latest if r[1] != row[1]]
        best = max(candidates, key=lambda r: dot(r[2], row[2])) if candidates else None  # first of the best, as maxByOrNull
        cosines += len(candidates)
        if best is not None:
            cosines += 1
            if dot(best[2], row[2]) >= t:
                sup[best[0]] = row[0]
                latest.remove(best)
        latest.append(row)
    return sup, cosines, len(rows)  # every row of the label is written


def relink_new(rows, t, dot, before):
    """One cosine per pair, no list per row, and only rows whose is_latest / superseded_by changed are written."""
    latest, sup, cosines = [], {}, 0
    for row in rows:
        best, best_cos = -1, -np.inf
        for i, r in enumerate(latest):
            if r[1] != row[1]:
                c = dot(r[2], row[2])
                cosines += 1
                if c > best_cos:
                    best, best_cos = i, c
        if best >= 0 and best_cos >= t:
            sup[latest[best][0]] = row[0]
            latest.pop(best)
        latest.append(row)
    writes = sum(before.get(r[0], "new") != sup.get(r[0]) for r in rows)
    return sup, cosines, writes


def relink_from(rows, t, dot, before, k):
    """relink_new starting at row k: rows before k keep their answer (later rows cannot change it); the latest at k are the
    earlier rows not replaced by an earlier row. Same answer as from row 0 when nothing before k was added or removed."""
    index = {r[0]: i for i, r in enumerate(rows)}
    sup = {r[0]: before[r[0]] for r in rows[:k] if before.get(r[0]) is not None and index.get(before[r[0]], k) < k}
    latest = [r for r in rows[:k] if r[0] not in sup]
    cosines = 0
    for row in rows[k:]:
        best, best_cos = -1, -np.inf
        for i, r in enumerate(latest):
            if r[1] != row[1]:
                c = dot(r[2], row[2])
                cosines += 1
                if c > best_cos:
                    best, best_cos = i, c
        if best >= 0 and best_cos >= t:
            sup[latest[best][0]] = row[0]
            latest.pop(best)
        latest.append(row)
    writes = sum(before.get(r[0], "new") != sup.get(r[0]) for r in rows)
    return sup, cosines, writes


def add_in_order(crops, order, dot):
    """Add the real crops clip by clip in [order] (a clip may come twice: a re-run), as the phone does, and check that
    relinking from the earliest changed time gives the same answer as relinking everything."""
    table, same, saved = {}, True, [0, 0]  # id -> (time, frame, vector, superseded_by)
    for clip in order:
        mine = [i for i, c in enumerate(crops) if c["clip"] == clip]
        removed = [i for i in table if crops[i]["clip"] == clip]
        for i in removed:
            del table[i]
        for i in mine:
            table[i] = None
        for label in {crops[i]["label"] for i in mine + removed}:
            ids = sorted((i for i in table if crops[i]["label"] == label), key=lambda i: ((crops[i]["clip"], crops[i]["frame_no"]), i))
            rows = [(i, (crops[i]["clip"], crops[i]["frame_no"]), np.array(crops[i]["vector"], dtype=np.float32)) for i in ids]
            before = {i: table[i] for i in ids}
            start = min((crops[i]["clip"], crops[i]["frame_no"]) for i in mine + removed if crops[i]["label"] == label)  # per label, as the phone
            k = next((n for n, r in enumerate(rows) if r[1] >= start), len(rows))
            full, cos_full, _ = relink_new(rows, CROP_COSINE_MIN, dot, before)
            part, cos_part, _ = relink_from(rows, CROP_COSINE_MIN, dot, before, k)
            same &= full == part
            saved[0] += cos_full; saved[1] += cos_part
            for i in ids:
                table[i] = full.get(i)
    return same, saved


def part3():
    dot = lambda a, b: float(a @ b)
    crops = json.loads(CROPS.read_text(encoding="utf-8"))["crops"]
    ordered = sorted(range(len(crops)), key=lambda i: (crops[i]["clip"], crops[i]["frame_no"], i))
    same, links = True, 0
    for label in sorted({c["label"] for c in crops}):
        rows = [(i, (crops[i]["clip"], crops[i]["frame_no"]), np.array(crops[i]["vector"], dtype=np.float32)) for i in ordered if crops[i]["label"] == label]
        for t in (0.80, 0.85, CROP_COSINE_MIN, 0.90):
            a, b = relink_now(rows, t, dot)[0], relink_new(rows, t, dot, {})[0]
            same &= a == b
            links += len(a) if t == CROP_COSINE_MIN else 0
    print(f"3 relink, 90 real Pixel crops, 4 thresholds: same links: {same}; {links} links at {CROP_COSINE_MIN}")
    orders = [["clip1", "clip2", "clip3", "clip4", "clip5", "clip6"], ["clip4", "clip1", "clip6", "clip2", "clip5", "clip3"],
              ["clip6", "clip5", "clip4", "clip3", "clip2", "clip1"], ["clip1", "clip2", "clip1", "clip4", "clip3", "clip4", "clip5", "clip6"]]
    from_same = True
    for order in orders:
        ok, (cos_full, cos_part) = add_in_order(crops, order, dot)
        from_same &= ok
        print(f"3 relink from the earliest changed time, clips added {' '.join(c[-1] for c in order)}: same links: {ok}; cosines {cos_full} all / {cos_part} from")
    same &= from_same
    growth = []
    if COCO.exists():
        vectors = np.fromfile(COCO, dtype=np.float32).reshape(-1, 512)
        per_video, rows = 20, []
        for video in range(1, 201):
            base = (video - 1) * per_video
            rows += [(base + k, (video, k // 4), vectors[base + k]) for k in range(per_video)]  # 20 sightings of one label, 4 per frame
            if video % 25 == 0 or video == 1:
                # What the table holds before this video's relink: the links of the earlier videos; new rows start as latest (NULL).
                before = relink_now(rows[:-per_video], CROP_COSINE_MIN, dot)[0]
                before = {r[0]: before.get(r[0]) for r in rows[:-per_video]} | {r[0]: None for r in rows[-per_video:]}
                start = time.perf_counter(); a, cos_a, w_a = relink_now(rows, CROP_COSINE_MIN, dot); ms_a = (time.perf_counter() - start) * 1000
                start = time.perf_counter(); b, cos_b, w_b = relink_new(rows, CROP_COSINE_MIN, dot, before); ms_b = (time.perf_counter() - start) * 1000
                start = time.perf_counter(); c, cos_c, _ = relink_from(rows, CROP_COSINE_MIN, dot, before, len(rows) - per_video); ms_c = (time.perf_counter() - start) * 1000
                same &= a == b == c
                growth.append({"sightings": len(rows), "now_cosines": cos_a, "new_cosines": cos_b, "from_cosines": cos_c, "now_writes": w_a,
                               "new_writes": w_b, "now_ms": ms_a, "new_ms": ms_b, "from_ms": ms_c, "same": a == b == c})
                print(f"3 relink, one label, {len(rows):5} sightings: cosines {cos_a:>9,} now / {cos_b:>9,} new / {cos_c:>6,} from; rows written {w_a:5} / {w_b:3}; "
                      f"{ms_a:7.0f} / {ms_b:7.0f} / {ms_c:4.0f} ms (Python); same: {a == b == c}")
    else:
        print(f"3 relink growth skipped: {COCO} not found (EYKO-91 COCO vectors)")
    return {"real_crops_same_links": same, "from_earliest_same_links": from_same, "links_at_threshold": links, "growth": growth}


# Measured on the phones, app in front, kit clips 1 and 2 (docs/results/2026-11-11-pixel-kit-clips-timing.md): sightings, seconds.
PHONES = {"Pixel 9 Pro XL": ((54, 12.5), (134, 33.9), "#eb6834"), "Infinix X670": ((53, 42.3), (134, 136.5), "#1baf7a")}


def plot(result):
    """Left: `latest` on the phones grows in a straight line with sightings. Right: relink comparisons as one label grows."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
    for name, (a, b, colour) in PHONES.items():
        left.plot([a[0], b[0]], [a[1], b[1]], color=colour, lw=2, marker="o", ms=8, label=name)
        left.annotate(f"{b[1] / b[0]:.2f} s per sighting", (b[0], b[1]), textcoords="offset points", xytext=(-8, 6), ha="right", fontsize=9)
    left.set(xlabel="sightings in the clip", ylabel="`latest` stage time (s)", title="Phones: `latest` time against sightings", xlim=(0, 150), ylim=(0, None))
    left.legend(frameon=False)
    growth = result["part3"]["growth"]
    x = [g["sightings"] for g in growth]
    right.plot(x, [g["now_cosines"] for g in growth], color="#6250d6", lw=2, marker="o", ms=8, label="now: the whole label again")
    right.plot(x, [g["from_cosines"] for g in growth], color="#2a78d6", lw=2, marker="o", ms=8, label="new: from the new video's time")
    right.set_yscale("log")
    right.set(xlabel="sightings of one label in the library (20 per video)", ylabel="cosines when one video is added (log)",
              title="relink: comparisons per added video (same links)")
    right.legend(frameon=False)
    for ax in (left, right):
        ax.grid(alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"latest-time-vs-sightings.{ext}", dpi=150)
    print(f"graph: {OUT / 'latest-time-vs-sightings.png'}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"part1": None, "part2": None, "part3": None}
    result["part1"], crops = part1()
    result["part2"] = part2(crops)
    result["part3"] = part3()
    (OUT / "latest-profile.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"written {OUT / 'latest-profile.json'}")
    plot(result)
    if not (result["part1"]["same_pixels"] and result["part3"]["real_crops_same_links"]):  # includes every growth step
        sys.exit("a faster version changed the output")


if __name__ == "__main__":
    main()
