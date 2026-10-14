# Detectors: YOLOX-Tiny against RF-DETR Nano and three open-vocabulary detectors (14 October 2026)

**In one line:** no closed-list detector can name keys, wallet, glasses or earbuds, because none of
them is among the 80 COCO classes; open-vocabulary detectors can. OWLv2 found 81 of 87 of our own
things (YOLOX-Tiny 7) and, at a stricter minimum chosen after seeing the results, 71 with 9 false
alarms. It costs about 4.7 s per frame on the laptop CPU, against 0.024 s for YOLOX-Tiny.

A laptop measurement (laptop first, winners to the phone). Nothing was built into the app.
Run with `task detector-bench -- run <model>` and `task detector-bench -- score`; raw output in
`D:/eykon-cache/bench/detectors/<model>.json`, table in `detectors/scores-2026-10-14.json`.

## Why

A suggestion (from a friend of the user) to try newer detectors: YOLO26n / YOLO11n, RF-DETR Nano,
YOLO-World / YOLOE for words chosen by us, plus phone speed tips. Licences checked first:

| Model | Licence | Tried |
|---|---|---|
| YOLO11, YOLO26 (Ultralytics) | AGPL-3.0 | No: project rule, no AGPL |
| YOLOE (THU-MIG) | AGPL-3.0 | No |
| YOLO-World (Tencent AILab) | GPL-3.0 | No: copyleft, same concern |
| RF-DETR Nano (Roboflow) | Apache-2.0 | Yes (80 COCO classes) |
| OWLv2 base, OmDet-Turbo Swin-T, Grounding DINO tiny | Apache-2.0 | Yes (open vocabulary, in place of YOLO-World / YOLOE) |

## What was run

- **ours44:** the 44 frames the Pixel kept on 13 October, labels
  `perception/presence-2026-10-13.csv` (phone, laptop, chair, backpack, car, monitor, papers,
  table tennis), as in the VLM benchmark.
- **own50:** one frame every 3 s of our clips S1-01 and S1-02 (640 px), labels
  `detectors/own-presence-2026-10-14.csv` (keys 22, wallet 16, glasses 13, earbuds 13, phone 11,
  pen 12 frames), written by the AI assistant from contact sheets before any detector ran.
- Closed-list models count a thing when one of its COCO classes is reported; open-vocabulary models
  are asked for the set's things by short phrases ("keys", "a wallet", "glasses", "earbuds", ...).
- Each model's own documented example minimum, not tuned: YOLOX 0.35 (the app's), RF-DETR 0.5,
  OWLv2 0.1, OmDet-Turbo 0.3, Grounding DINO 0.4 (text 0.3).
- Laptop CPU (i5-13420H); ms per frame after loading. Not phone numbers.

## Result (fixed minimums)

Found = named when present; false = named when absent.

| Model | ours44 found | false | own50 found | false | ms / frame | peak MB |
|---|---|---|---|---|---|---|
| YOLOX-Tiny (app) | 30 of 88 | 6 of 264 | 7 of 87 | 10 of 213 | 24 | 516 |
| RF-DETR Nano | 41 of 88 | 9 of 264 | 8 of 87 | 9 of 213 | 176 | 907 |
| OmDet-Turbo | 81 of 88 | 92 of 264 | 77 of 87 | 71 of 213 | 1100 | 1020 |
| Grounding DINO tiny | 37 of 88 | 53 of 264 | 63 of 87 | 16 of 213 | 7806 | 2516 |
| OWLv2 base | 86 of 88 | 117 of 264 | 81 of 87 | 67 of 213 | 4664 | 1169 |

Our own things (found of present | false):

| Model | keys | wallet | glasses | earbuds | pen | phone |
|---|---|---|---|---|---|---|
| YOLOX-Tiny | 0/22 | 0/16 | 0/13 | 0/13 | 0/12 | 7/11, 10 false |
| RF-DETR Nano | 0/22 | 0/16 | 0/13 | 0/13 | 0/12 | 8/11, 9 false |
| OmDet-Turbo | 21/22, 11 false | 15/16, 9 | 13/13, 5 | 6/13, 9 | 12/12, 16 | 10/11, 21 |
| Grounding DINO | 17/22, 0 | 16/16, 11 | 7/13, 0 | 0/13, 2 | 12/12, 1 | 11/11, 2 |
| OWLv2 | 22/22, 18 | 16/16, 2 | 13/13, 1 | 9/13, 11 | 12/12, 21 | 9/11, 14 |

## Stricter minimums (chosen after the results above were seen)

Not a held-out result: a pointer for the next test. OWLv2 and OmDet-Turbo kept every box above
0.05, so the same runs can be scored at other minimums (found | false).

| Model | Set | 0.2 | 0.4 | 0.5 | 0.6 |
|---|---|---|---|---|---|
| OWLv2 | own50 | 75 / 87 \| 26 | **71 \| 9** | 67 \| 2 | 55 \| 1 |
| OWLv2 | ours44 | 85 / 88 \| 82 | 67 \| 19 | 34 \| 5 | 12 \| 0 |
| OmDet-Turbo | own50 | 87 \| 141 | 66 \| 31 | 53 \| 10 | 39 \| 3 |
| OmDet-Turbo | ours44 | 88 \| 157 | 67 \| 52 | 40 \| 21 | 23 \| 8 |

## What it means

- **The suggestion's main pick (YOLO26n / YOLO11n) is not usable here** (AGPL). The Apache
  alternative in the same class, RF-DETR Nano, finds a little more of the COCO things (41 against
  30 of 88) at about 7 times YOLOX-Tiny's time, and still names none of keys, wallet, glasses,
  earbuds or pen. Swapping the closed-list detector does not fix the captions.
- **Open vocabulary is the real gain.** OWLv2 is the most accurate and has ready ONNX files
  (`Xenova/owlv2-base-patch16-ensemble`: 614 MB fp32, 155 MB 8-bit), the same runtime the app
  already uses. OmDet-Turbo is 4 times faster on the laptop but has no official ONNX file and many
  more false alarms. Grounding DINO is slow and misses earbuds.
- **Cost:** OWLv2 at about 4.7 s per frame on the laptop; the app keeps 10 to 16 frames per 75 s
  clip, so it would be minutes per clip on the phone if it ran on every kept frame. Workable only
  as a background step, like the VLM.
- **Speed tips in the suggestion** (smaller input, int8, detect every few frames with a tracker)
  matter for live video. The app works on recorded clips and already looks at one kept frame per
  3 s slot at 416 px; the detector is 244 ms of that on the Pixel, not the bottleneck.

## Follow-up, same evening: OWL-ViT, the 8-bit OWLv2 file, and OWLv2 on the Pixel

Same sets, phrases and minimum (0.1) as OWLv2; both added to the script before they ran.

| Model | ours44 found | false | own50 found | false | ms / frame (laptop) | own50 at 0.4 (post hoc) |
|---|---|---|---|---|---|---|
| OWLv2 base (full precision) | 86 of 88 | 117 | 81 of 87 | 67 | 4664 | 71 \| 9 |
| OWLv2 base, 8-bit ONNX (`Xenova/...` `model_quantized.onnx`, 155 MB) | 86 of 88 | 159 | 72 of 87 | 65 | 3141 | 55 \| 12 |
| OWL-ViT base patch32 (Apache-2.0) | 54 of 88 | 82 | 32 of 87 | 33 | 686 | 16 \| 7 |

- **OWL-ViT patch32 is out:** 7 times faster but names no keys (0 of 22) and no earbuds (0 of 13).
- **The 8-bit file loses accuracy:** at 0.4 it finds 55 against 71 of our things; earbuds fall to
  3 of 13 at the documented minimum (full precision 9).

**On the Pixel 9 Pro XL** (`OwlPhoneBenchmarkTest`, the 8-bit file, onnxruntime-android 1.18.0,
default CPU options, five of our frames already turned into the model's input on the laptop;
raw output `detectors/pixel9proxl-owlv2-q8-2026-10-14.json`; battery 32.4 °C, 69 %):

| Measure | Value |
|---|---|
| Loading the model | 1.5 s |
| Model run per frame | 8.3 to 9.5 s (five frames) |
| Native memory at peak | 4.9 GB |
| Largest score difference from the laptop running the same file | 0.10 to 0.32 per frame |

- About 9 s per kept frame means 1.5 to 2.5 minutes for a 75 s clip (10 to 16 kept frames),
  in the background, with close to 5 GB of memory. Too heavy to run on every kept frame.
- **The phone does not give the laptop's answer** on the same 8-bit file: "keys" on S1-01 at
  16.5 s scores 0.53 on the laptop and 0.37 on the phone, so a 0.4 minimum would flip. Likely the
  different 8-bit maths on ARM and x86 and the older runtime in the app (1.18.0); not looked into.
  Any minimum must be set from phone runs, not laptop runs.

## Not done yet

- A held-out check of the 0.4 minimum on the sealed clips (S1-03, S1-06): waits for the user's
  decision, because those clips are kept for the final test.
- Why the phone's scores differ (runtime version, 8-bit kernels); the fp16 file (308 MB) as a check.
- The "earbuds" phrase: the visible thing is the case; the phrase was fixed before the run.
- YOLOX-Tiny's load time (77.8 s) includes importing the MobileCLIP tools; not its real load cost.
