"""Better action labels from the frames' stored MobileCLIP vectors (card EYKO-60). No model re-runs on pictures.
    task ego4d-actions -- [A|B] [<variant> ...]     default: every variant, set A (choose there; B only reports)

Variants, fixed before scoring (20 October 2026):
  app          the 8 phrases the app ships (scene_prompts.json), share >= 0.30: the baseline
  wearer       the same 8 actions in first-person words, plus the missing ones (phone, drink, cut, wash dishes,
               write, stairs), one phrase each, share >= 0.30
  ensemble     like wearer, but each action is the average vector of three phrasings (CLIP's prompt ensembling)
  +smooth N    each frame takes the action with the highest share summed over itself and its neighbours within
               N seconds (kept frames only), then the 0.30 floor
  +floor F     a lower share floor (more frames get a label)
Chosen on set A by F1 of "instance found" and "label precision" over every MQ class we want (ego4d_eval.mq).
"""
import json
import sys

import numpy as np
import onnxruntime as ort
import open_clip

from src.benchmarks import ego4d_eval as ev
from src.benchmarks.ego4d_pipeline import ASSETS, RUN

WEARER = {  # our action name -> one first-person phrase
    "picking something up": "a first-person photo of my hand picking up an object",
    "putting something down": "a first-person photo of my hand putting an object down on a surface",
    "typing on a laptop": "a first-person photo of my hands typing on a laptop keyboard",
    "cooking": "a first-person photo of my hands stirring food in a pan on a stove",
    "walking": "a first-person photo while walking outside along a street",
    "talking to someone": "a first-person photo of a person in front of me talking to me",
    "reading": "a first-person photo of a book or paper held open in my hands",
    "eating": "a first-person photo of me eating food",
    "using a phone": "a first-person photo of a phone screen held in my hand",
    "drinking": "a first-person photo of me drinking from a cup or bottle",
    "cutting food": "a first-person photo of my hands cutting vegetables with a knife on a board",
    "washing dishes": "a first-person photo of my hands washing dishes in a sink",
    "writing": "a first-person photo of my hand writing with a pen on paper",
    "climbing stairs": "a first-person photo of walking up or down stairs",
}
EXTRA = {  # two more phrasings each for the ensemble
    "picking something up": ["my hand grabbing a thing from a table", "reaching out to pick something up"],
    "putting something down": ["my hand placing a thing on a table", "setting an object down"],
    "typing on a laptop": ["hands on a laptop keyboard", "working on a computer"],
    "cooking": ["cooking in a kitchen", "food cooking in a pot"],
    "walking": ["walking on a sidewalk", "a street seen while walking"],
    "talking to someone": ["a conversation with a person facing me", "a person looking at me and speaking"],
    "reading": ["reading a book", "pages of a book in my hands"],
    "eating": ["eating a meal", "food on a plate in front of me being eaten"],
    "using a phone": ["looking at my smartphone", "a hand holding a mobile phone with the screen on"],
    "drinking": ["drinking a beverage", "a cup raised to my mouth"],
    "cutting food": ["chopping food on a cutting board", "a knife slicing vegetables"],
    "washing dishes": ["washing plates under a tap", "a sink full of dishes being washed"],
    "writing": ["writing notes in a notebook", "a pen on a paper page"],
    "climbing stairs": ["stairs in front of me", "a staircase seen from above while walking down"],
}
WEARER_MAP = ev.MAP | {
    "use_phone": "using a phone", "drink_beverage": "drinking", '"cut_/_chop_/_slice_a_vegetable,_fruit,_or_meat"': "cutting food",
    "wash_dishes_/_utensils_/_bakeware_etc.": "washing dishes", "write_notes_in_a_paper_/_book": "writing",
    "walk_down_stairs_/_walk_up_stairs": "climbing stairs",
}


class Encoder:
    def __init__(self):
        self.tok = open_clip.get_tokenizer("MobileCLIP-S2")
        self.session = ort.InferenceSession(str(ev.TEXT_MODEL), providers=["CPUExecutionProvider"])

    def __call__(self, text: str) -> np.ndarray:
        return self.session.run(None, {"tokens": self.tok([text]).numpy().astype(np.int64)})[0][0]


def prompt_sets(enc: Encoder) -> dict[str, tuple[list[str], np.ndarray]]:
    app = json.loads((ASSETS / "scene_prompts.json").read_text(encoding="utf-8"))["actions"]
    unit = lambda v: v / np.linalg.norm(v)
    return {
        "app": (list(app), np.array(list(app.values()), dtype=np.float32)),
        "wearer": (list(WEARER), np.stack([enc(p) for p in WEARER.values()])),
        "ensemble": (list(WEARER), np.stack([unit(np.mean([enc(p) for p in [WEARER[a], *EXTRA[a]]], 0)) for a in WEARER])),
    }


def labeller(names: list[str], texts: np.ndarray, smooth: float, floor: float):
    def label(uid: str, kept: list[dict]) -> list[str | None]:
        image = np.load(RUN / f"{uid}.npz")["image"]
        logits = 100 * image @ texts.T
        p = np.exp(logits - logits.max(1, keepdims=True))
        p /= p.sum(1, keepdims=True)
        times = np.array([k["t"] for k in kept])
        out = []
        for i in range(len(kept)):
            near = np.abs(times - times[i]) <= smooth
            share = p[near].mean(0)
            out.append(names[int(share.argmax())] if share.max() >= floor else None)
        return out
    return label


def main(which: str = "A", *only: str) -> None:
    ev.SET = which
    sets = prompt_sets(Encoder())
    variants = {}
    for name, (names, texts) in sets.items():
        mapping = ev.MAP if name == "app" else WEARER_MAP
        for smooth in (0.0, 3.0, 6.0):
            for floor in (0.30, 0.20):
                key = f"{name} smooth {smooth:g} floor {floor:.2f}"
                if only and key not in only:
                    continue
                variants[key] = ev.mq(labeller(names, texts, smooth, floor), mapping)
    for key, r in sorted(variants.items(), key=lambda kv: -kv[1]["summary"]["F1"]):
        print(f"{r['summary']['F1']:5.1f} F1  found {r['summary']['found']:5.1f}  precision {r['summary']['precision']:5.1f}  R@1 {r['summary']['R@1 tIoU>=0.5']:4.1f}  {key}")
    ev.OUT.mkdir(parents=True, exist_ok=True)
    (ev.OUT / f"actions-{which}.json").write_text(json.dumps(variants, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:])
