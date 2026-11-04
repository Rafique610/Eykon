"""Laptop measurement for card EYKO-32: D-FINE (Objects365) on every kept frame, plus OWLv2 only on
frames a cheap signal picks. How much accuracy does each way of picking keep, and at what cost?
No model is run again for the detectors: the per-frame best scores saved by detector_bench are reused.

    task detector-hybrid

Fixed before any mix was scored (14 October 2026):
  split    D-FINE answers for every thing except keys and earbuds; OWLv2 answers for keys and earbuds
           (and papers, table tennis, which D-FINE lacks). This split comes from the detector sweep the
           same evening (D-FINE named no keys or earbuds), so it is not a held-out choice.
  minimum  D-FINE 0.5 (documented); OWLv2 0.1 (documented) and 0.4 (chosen after the sweep)
  pickers  which frames OWLv2 sees:
             none      D-FINE only
             all       OWLv2 on every frame
             third     every third frame in time order (a fixed budget of 1 in 3)
             dfine     D-FINE already sees a phone, key, earphone or wallet at a score of at least 0.1
             clip      MobileCLIP-S2: the frame's picture vector is among the top third of frames by
                       likeness to "a photo of keys" or "a photo of earbuds" (the same 1 in 3 budget;
                       the phone already stores this vector for every kept frame)
  union    a second scoring where, on the frames OWLv2 sees, either model may name any thing
  cost     OWLv2 frames as a share of all frames, and the Pixel time that share would add for a
           75 s clip with 13 kept frames at the 9 s per frame measured on the Pixel (8-bit file)
"""
import csv
import json
from pathlib import Path

import numpy as np

from src.benchmarks.detector_bench import FLOOR, OUT, ROOT, SETS, labelled

DFINE = "dfine_s_obj365"
OWL_THINGS = {"keys", "earbuds", "papers", "table_tennis"}
OWL_MINS = (0.1, 0.4)
DFINE_MIN = 0.5
CUE = ("phone", "keys", "earbuds", "wallet")
CUE_MIN = 0.1
CLIP_PHRASES = ("a photo of keys", "a photo of earbuds")
PIXEL_OWL_S, KEPT_PER_CLIP = 9.0, 13


def best(model: str) -> dict[str, dict[str, dict]]:
    sets = json.loads((ROOT / f"{model}.json").read_text(encoding="utf-8"))["sets"]
    return {s: {f["frame"]: f.get("best", {}) for f in frames} for s, frames in sets.items()}


def clip_likeness() -> dict[str, float]:
    """Best likeness of each frame to CLIP_PHRASES, cached on D: (MobileCLIP-S2, as on the phone)."""
    cache = ROOT / "clip_likeness.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    import open_clip
    import torch
    from PIL import Image
    from timm.utils import reparameterize_model
    model, _, preprocess = open_clip.create_model_and_transforms("MobileCLIP-S2", pretrained="datacompdr", device="cpu")
    model = reparameterize_model(model.eval())
    tokenizer = open_clip.get_tokenizer("MobileCLIP-S2")
    out = {}
    with torch.no_grad():
        texts = torch.nn.functional.normalize(model.encode_text(tokenizer(list(CLIP_PHRASES))), dim=-1)
        for folder, _ in SETS.values():
            for path in sorted(folder.glob("*.jpg")):
                image = torch.nn.functional.normalize(model.encode_image(preprocess(Image.open(path).convert("RGB"))[None]), dim=-1)
                out[path.stem] = round(float((image @ texts.T).max()), 4)
    cache.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def picked(picker: str, frames: list[str], dfine: dict, likeness: dict) -> set[str]:
    if picker == "none":
        return set()
    if picker == "all":
        return set(frames)
    if picker == "third":
        return set(frames[::3])
    if picker == "dfine":
        return {f for f in frames if max(dfine[f].get(t, 0.0) for t in CUE) >= CUE_MIN}
    ranked = sorted(frames, key=lambda f: -likeness[f])
    return set(ranked[: round(len(frames) / 3)])


def main(dfine: str = DFINE, owl: str = "owlv2", sets: tuple[str, ...] = tuple(SETS), owl_mins: tuple[float, ...] = OWL_MINS,
         out: str = "hybrid-2026-10-14.json", owl_s: float = PIXEL_OWL_S) -> None:
    assert FLOOR <= CUE_MIN
    dfine, owl, likeness = best(dfine), best(owl), clip_likeness()
    table = []
    for owl_min in owl_mins:
        for union in (False, True):
            for picker in ("none", "all", "third", "dfine", "clip"):
                row = {"owl_min": owl_min, "union": union, "picker": picker, "sent": 0, "frames": 0}
                for set_name in sets:
                    things, rows = labelled(set_name)
                    frames = [r["frame"] for r in rows]
                    chosen = picked(picker, frames, dfine[set_name], likeness)
                    row["sent"] += len(chosen)
                    row["frames"] += len(frames)
                    per = {t: [0, 0] for t in things}
                    for r in rows:
                        f = r["frame"]
                        for t in things:
                            by_dfine = t not in OWL_THINGS and dfine[set_name][f].get(t, 0.0) >= DFINE_MIN
                            by_owl = f in chosen and (union or t in OWL_THINGS) and owl[set_name][f].get(t, 0.0) >= owl_min
                            if by_dfine or by_owl:
                                per[t][0 if r[t] == "1" else 1] += 1
                    row[set_name] = {"found": sum(p[0] for p in per.values()), "false": sum(p[1] for p in per.values()),
                                     "present": sum(int(r[t]) for r in rows for t in things), "per_thing": per}
                share = row["sent"] / row["frames"]
                row["share"], row["pixel_s_per_clip"] = round(share, 2), round(share * KEPT_PER_CLIP * owl_s)
                table.append(row)
    print(f"{'owl min':>8}{'union':>7}{'picker':>8}{'OWLv2 on':>10}{'+s/clip':>9}" + "".join(f"{s + ' found':>14}{'false':>7}" for s in sets)
          + "   own50 keys/wallet/glasses/earbuds/pen")
    for r in table:
        p = r["own50"]["per_thing"]
        print(f"{r['owl_min']:>8}{str(r['union']):>7}{r['picker']:>8}{r['share']:>9.0%}{r['pixel_s_per_clip']:>9}"
              + "".join(f"{r[s]['found']:>9} of {r[s]['present']:<3}{r[s]['false']:>4}" for s in sets)
              + "   " + " ".join(f"{p[t][0]}" for t in ("keys", "wallet", "glasses", "earbuds", "pen")))
    (OUT / out).write_text(json.dumps(table, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
