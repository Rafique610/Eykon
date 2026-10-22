# EYKO-9: perception Option A on the phone (13 October 2026)

**In one line:** the detector and the MobileCLIP phrase scorer run on the Pixel and match the
laptop, and people are found reliably; but YOLOX-Nano finds only 4 of 32 everyday things in our
own frames (YOLOX-Tiny 18), and the place phrase never says "none of these".

**Decision, 13 October 2026 (Rafique): the app uses YOLOX-Tiny.** The first sections below are
the Nano measurement that led to it.

## What was run

- Phone: Google Pixel 9 Pro XL, Android 17, debug build, CPU, 4 threads.
- Frames: the six evaluation clips (`files/eval_clips/clip1..6.mp4`) went through the app's own
  stages (pull frames, cheap filters, drop repeats). All 44 frames that were kept were described
  by `OptionA.describe`.
- Settings: detector confidence 0.35, phrase minimum 0.30 (the card's starting values, untuned).
- Labels: `perception/labels-2026-10-13.csv`, written by the AI assistant from the pictures
  before the phone's answers were pulled. **Not yet checked by a person.**
- Raw phone output: `perception/pixel9proxl-2026-10-13-nano.json` (the evening run; the morning
  run gave the same things on every frame, and the times in the first tables below are the
  morning's). Scored with `task eval-perception`.

Scoring rules (fixed before reading the answers) are in `src/benchmarks/perception_score.py`.

## Phone and laptop agree

| Check | Laptop | Phone |
|---|---|---|
| YOLOX demo picture (`dog.jpg`), confidence | dog 0.855, bicycle 0.803, car 0.798 | dog 0.855, bicycle 0.804, car 0.797 |
| Same picture, place shares | "a shop" 0.691 | "a shop" 0.711 |
| Same picture, action shares | "picking something up" 0.699 | "picking something up" 0.729 |
| The 44 real frames, same list of things | | 41 of 44 frames |

## Accuracy on the 44 frames

| Measure | Result |
|---|---|
| Main object (the card's measure; 80 % asked) | 43 of 44 (98 %) |
| ... of which the main object is a person | 40 of 40 |
| ... of which it is another thing (backpack, car) | 1 of 2 |
| ... of which nothing the detector knows is in view, and nothing was reported | 2 of 2 |
| Most prominent thing that is not a person (phone, laptop, chair, monitor, backpack, car) | **4 of 32 (12 %)** |
| Place, all frames | 23 of 44 (52 %) |
| Place, frames whose real place is one of the nine phrases | 23 of 34 (68 %) |
| Place, frames whose real place is not on the list (cafeteria, terrace): "none" given | 0 of 10 |

How the 98 % could be lying: 40 of the 44 frames have a person as the main thing, and the
detector is good at people. The card's measure passes, but it says almost nothing about finding
objects, which is this project's first job. The fourth row is the honest one.

What the detector listed over all frames: dining table 15, chair 14, laptop 5, cake 3, book 2,
suitcase 2, refrigerator 1, bed 1, car 1. Phones lying on desks were missed every time (twice
called "cake" or "book"); the laptop on a lap in the corridor clip was missed in all five frames.

Places given: "a classroom" 35, "an office" 6, "a street" 2, "inside a car" 1. The cafeteria and
the terrace were both called "a classroom". The corridor was never called "a hallway". A share
of 0.30 out of nine phrases is a low bar, so a place is almost always given.

Actions given (not labelled, so not scored): reading 23, typing on a laptop 8, walking 5, picking
something up 3, talking to someone 2, putting something down 1, none 2.

## Cost on the Pixel

| Measure | Per frame |
|---|---|
| Detector + image model + phrases | median 705 ms, worst 905 ms |
| Detector + phrases, reusing the image vector the dedup stage saved | median 119 ms, worst 170 ms |
| Peak memory | native 344 MB, java 162 MB |

Every frame that reaches this step already has a saved vector, so the real added cost is the
second row. The first call on a cold app also loads the models; that is inside the "worst" value
of the first frame only.

## Laptop side check: is it the model or the threshold?

Same 44 frames, same labels, official YOLOX ONNX files, laptop CPU. Run after the Nano result was
seen, so it is a pointer for a decision, not a held-out result.

| Model (input) | File | Confidence | Non-person thing found | Person found | Laptop ms per frame |
|---|---|---|---|---|---|
| Nano (416) | 3.7 MB | 0.35 | 4 of 32 | 40 of 40 | 24 |
| Nano (416) | | 0.25 | 4 of 32 | 40 of 40 | 24 |
| Tiny (416) | 20 MB | 0.35 | 18 of 32 | 40 of 40 | 52 |
| Tiny (416) | | 0.25 | 19 of 32 | 40 of 40 | 47 |
| S (640) | 36 MB | 0.35 | 20 of 32 | 40 of 40 | 161 |
| S (640) | | 0.25 | 22 of 32 | 40 of 40 | 158 |

Lowering the threshold does not help Nano. YOLOX-Tiny (same licence, same input size, so the
same phone code with a different file) finds four to five times as many things for about twice
the detector time.

## Nano against Tiny on the Pixel (evening run, same day)

Same phone, same 44 frames, same labels, same code; only the detector file differs
(`PerceptionBenchmarkTest` with `-e detector yolox_tiny.onnx`). Nano ran first, Tiny straight
after. Raw output: `perception/pixel9proxl-2026-10-13-nano.json` and `...-tiny.json`.

| Measure | YOLOX-Nano (3.7 MB) | YOLOX-Tiny (20 MB) |
|---|---|---|
| Main object | 43 of 44 | 43 of 44 |
| Most prominent non-person thing | 4 of 32 (12 %) | **18 of 32 (56 %)** |
| Detector + phrases, saved image vector, median per frame | 102 ms | 244 ms |
| ... worst frame | 135 ms | 320 ms |
| Detector + image model + phrases, median per frame | 638 ms | 876 ms |
| Peak native memory | 341 MB | 392 MB |
| Boxes reported over all frames (people included) | 192 | 277 |

Tiny by thing: found cell phone 5, chair 6, laptop 5, monitor 1, car 1; missed cell phone 7,
chair 2, laptop 2, monitor 1, backpack 2. Place and action are unchanged, as they do not use the
detector. Nano gave the same things on all 44 frames as in the morning run.

Caveats: the battery was 32.1 °C before Nano and 35.9 °C before Tiny, so Tiny's times may be
slightly worse than a cool phone would give. Tiny's extra boxes were not checked for false
alarms (it reported one "airplane" and one "clock"); only the labelled thing per frame was
scored.

## After the switch to Tiny

`ObjectDetector.MODEL_FILE` is now `yolox_tiny.onnx`; settings, `task pull-detector` and the
laptop reference follow. On the Pixel all 31 video tests pass, and the phone matches the laptop
on the demo picture: bicycle 0.886, car 0.700, cat 0.553 against 0.887, 0.699, 0.555.

Tiny calls the dog in that picture a cat (Nano said dog, 0.855). The input preparation was
checked against two other conventions and is correct, so this is a real mistake of the model:
Tiny finds more things than Nano but is not always right about what they are.

Whether typed-phrase search over the frame vectors covers what the detector misses is in
`2026-10-13-frame-search-probe.md`.

## Limits

- 44 frames from six short clips, five of them indoors on one campus; one person labelled them
  (an AI), no second marker.
- These clips were also used for the keyframe work (EYKO-45), so they are not unseen data.
- Debug build; one phone. The Samsung A32 was not run.
- Actions were not labelled.
