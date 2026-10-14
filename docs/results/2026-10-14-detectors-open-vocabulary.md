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

## Reference only: YOLOE-11S (AGPL-3.0, cannot ship)

Run at the user's request to see what the AGPL option would have given. Laptop only, through a
one-off `uv run --with ultralytics` (Ultralytics 8.4.177); not added to `pyproject.toml` or the
Taskfile. Same sets and phrases; Ultralytics' default minimum 0.25, fixed before the run.

| Model | ours44 found | false | own50 found | false | ms / frame (laptop) |
|---|---|---|---|---|---|
| YOLOX-Tiny (app) | 30 of 88 | 6 | 7 of 87 | 10 | 24 |
| YOLOE-11S | 39 of 88 | 3 | 20 of 87 | 0 | 753 |
| OWLv2 base | 86 of 88 | 117 | 81 of 87 | 67 | 4664 |

Our own things for YOLOE-11S: keys 0 of 22, wallet 9 of 16, glasses 0 of 13, earbuds 1 of 13,
pen 9 of 12, phone 1 of 11; no false alarms. Lower minimums (post hoc): 0.2 gives 25 of 87 with
2 false. **It is very careful and misses most of our things**: on these clips it is far behind
OWLv2 and would not be worth a licence even if one were bought.

## Wider sweep after AGPL was allowed (academic only)

The user allowed AGPL models while the project is academic (`docs/invariants/tooling.md`, changed
14 October 2026). Same sets and scoring. Closed lists were matched to our things from the class
names only, before any of these models saw a frame (`VOCAB` in the script). Minimum: Ultralytics'
default 0.25; D-FINE's documented 0.5.

| Model | Licence | Classes | ours44 found | false | own50 found | false | ms / frame (laptop) |
|---|---|---|---|---|---|---|---|
| YOLOX-Tiny (app) | Apache | 80 COCO | 30 of 88 | 6 | 7 of 87 | 10 | 24 |
| YOLO11n | AGPL | 80 COCO | 31 | 13 | 8 | 10 | 54 |
| YOLO26n | AGPL | 80 COCO | 30 | 10 | 8 | 4 | 49 |
| YOLOv8s Open Images V7 | AGPL | 601 | 3 | 0 | 4 | 0 | 137 |
| YOLOE-11S, its own 4585-class list | AGPL | 4585 | 45 | 21 | 9 | 13 | 216 |
| YOLOE-11S, our phrases | AGPL | open | 39 | 3 | 20 | 0 | 753 |
| YOLOE-11L, our phrases | AGPL | open | 39 | 1 | 44 | 6 | 544 |
| **D-FINE S, Objects365** | **Apache** | 365 | 39 | 24 | 37 | 12 | 370 |
| **D-FINE M, Objects365** | **Apache** | 365 | 48 | 26 | 42 | 11 | 654 |
| OWLv2 base, our phrases | Apache | open | 86 | 117 | 81 | 67 | 4664 |

Our own things (found of present, false alarms after the comma when not 0):

| Model | keys /22 | wallet /16 | glasses /13 | earbuds /13 | pen /12 | phone /11 |
|---|---|---|---|---|---|---|
| YOLO11n / YOLO26n | 0 | 0 | 0 | 0 | 0 | 8, 10 / 8, 4 |
| YOLOE-11L, our phrases | 13 | 10, 3 | 5, 1 | 4, 2 | 9 | 3 |
| D-FINE S, Objects365 | 0 | 10 | 9 | 0 | 10 | 8, 12 |
| D-FINE M, Objects365 | 0 | 12 | 11 | 0 | 10 | 9, 11 |
| OWLv2 | 22, 18 | 16, 2 | 13, 1 | 9, 11 | 12, 21 | 9, 14 |

- **The newer COCO models (YOLO11n, YOLO26n) change nothing for us:** same 80 objects, same
  result as YOLOX-Tiny, about twice its laptop time.
- **Big fixed lists help only when the list has our things and the model has seen them:**
  Open Images V7 and YOLOE's own 4585-class list have "glasses", "key", "earphone" and "pen", but
  name almost none of them in our frames (the glasses were called a "handkerchief").
- **Objects365 (D-FINE) is the best closed-list option and it is Apache-2.0:** wallet, glasses and
  pen without false alarms, at 0.37 s (S) per laptop frame, about 13 times faster than OWLv2. It
  never named keys or the earbud case, and calls the wallet / earbud case a phone 11 to 12 times.
- **YOLOE-11L is the best AGPL result:** keys 13 of 22, few false alarms, 0.54 s, but it is still
  below OWLv2 on every one of our things.
- **No single fast model covers all four objects.** OWLv2 does, at about 9 s per frame on the Pixel.

## Mixing the two: D-FINE on every frame, OWLv2 only on picked frames

`task detector-hybrid` (`src/benchmarks/detector_hybrid.py`), from the saved per-frame scores; no
detector was run again. D-FINE S (Objects365) answers for everything except keys and earbuds; OWLv2
answers for those. This split comes from the sweep above, so it is not held out. "Union" lets OWLv2
also name D-FINE's things on the frames it sees. Pixel cost = share of frames OWLv2 sees x 13 kept
frames per 75 s clip x 9 s (the Pixel's 8-bit time); D-FINE's own phone time is not measured yet.

| Which frames OWLv2 sees | OWLv2 on | + Pixel s per clip | own50 found / false (OWLv2 min 0.1) | (min 0.4) | keys /22 (0.1) |
|---|---|---|---|---|---|
| None (D-FINE only) | 0 % | 0 | 37 / 12 | 37 / 12 | 0 |
| Every third frame | 34 % | 40 | 48 / 20 | 44 / 12 | 7 |
| D-FINE already sees a phone / key / earphone / wallet (score 0.1) | 82 % | 96 | 63 / 41 | 53 / 12 | 17 |
| **MobileCLIP: top third by likeness to "keys" / "earbuds"** | 34 % | 40 | **53 / 18** | **50 / 12** | **13** |
| All frames | 100 % | 117 | 68 / 41 | 58 / 12 | 22 |
| All frames, union | 100 % | 117 | 81 / 68 | 71 / 16 | 22 |

- **Picking by MobileCLIP beats a fixed every-third-frame budget at the same cost:** keys 13
  against 7, all own things 53 against 48. The phone already stores this vector for every kept
  frame, so the picking itself costs nothing extra.
- **D-FINE as the picker does not save much:** it flags 82 % of frames (it sees "phones"
  everywhere).
- **Earbuds are the weak point:** OWLv2's earbud scores stay under 0.4, so at that minimum no mix
  finds them; at 0.1 they come with false alarms.
- **Cost:** with one frame in three sent to OWLv2, a 75 s clip takes about 40 s more on the Pixel
  in the background. The app works on recorded clips, so this is processing time per clip, not a
  frame rate.
- Not measured: D-FINE's own time on the phone (laptop 0.37 s per frame); the phone's lower OWLv2
  scores (see above) would change which minimum to use.

## The mix on the Pixel (15 October 2026, 00:20)

`HybridPhoneBenchmarkTest`: D-FINE S Objects365 (full precision ONNX, `onnx-community/dfine_s_obj365-ONNX`,
42 MB) and the 8-bit OWLv2 on all 50 own frames on the Pixel 9 Pro XL, inputs prepared on the laptop
(`task hybrid-phone -- inputs`), scored with the same rules (`task hybrid-phone -- score`). Raw
output `detectors/pixel9proxl-hybrid-2026-10-15.json`, table `detectors/hybrid-pixel-2026-10-15.json`.
Only the test package was installed; the app was not changed. Battery 32.7 °C at the start, 37.8 °C
at the end (12 minutes).

**D-FINE needed one setting:** onnxruntime-android 1.18.0 (the app's version) fails on D-FINE's
`ScatterND` node with the default graph optimisation; with optimisation off it runs. The same file
runs with default settings in onnxruntime 1.18.0 on the laptop, so it is a phone-side runtime issue.

| Measure on the Pixel | D-FINE S | OWLv2 8-bit |
|---|---|---|
| Loading | 0.2 s | 1.4 s |
| Per frame (median of 50) | 0.96 s | 13.3 s |
| Same answers as the laptop running the same file | yes (largest difference 0.001) | no (up to 0.32) |
| Native memory at peak (both loaded) | 5.2 GB | |

Mixes, scored from the phone's own answers (own50: found of 87 / false of 213; keys of 22; added time
for a 75 s clip with 13 kept frames, at the Pixel's medians):

| OWLv2 sees | OWLv2 min | Found | False | Keys | Earbuds | Pixel s per clip |
|---|---|---|---|---|---|---|
| None (D-FINE only) | - | 37 | 12 | 0 | 0 | 12 |
| Every third frame | 0.1 | 47 | 21 | 7 | 3 | 12 + 59 |
| **MobileCLIP top third** | **0.1** | **53** | **16** | **13** | 3 | **12 + 59** |
| **MobileCLIP top third** | **0.3** | **50** | **12** | **13** | 0 | **12 + 59** |
| All frames | 0.3 | 58 | 13 | 21 | 0 | 12 + 173 |
| All frames, union | 0.3 | 71 | 24 | 21 | 0 | 12 + 173 |

- **On the phone the mix holds up:** D-FINE plus OWLv2 on the third of frames MobileCLIP picks finds
  50 of 87 own things with the same 12 false alarms as D-FINE alone (13 more keys, no new false
  alarms) at OWLv2 minimum 0.3; 53 with 16 false at 0.1. The minimums are chosen after seeing results.
- **Cost:** about 71 s of background work for a 75 s clip (D-FINE 12 s, OWLv2 59 s), against about
  3 s for today's YOLOX-Tiny step. Memory peaks at 5.2 GB with both models loaded.
- **Earbuds:** the phone's OWLv2 scores for the earbud case stay below 0.3; only 3 of 13 at 0.1.
- OWLv2 was slower here (13.3 s) than in the five-frame test (8.3 to 9.5 s); the phone was warmer
  and ran D-FINE alongside.

## Not done yet

- A held-out check of the 0.4 minimum on the sealed clips (S1-03, S1-06): waits for the user's
  decision, because those clips are kept for the final test.
- Why the phone's scores differ (runtime version, 8-bit kernels); the fp16 file (308 MB) as a check.
- The "earbuds" phrase: the visible thing is the case; the phrase was fixed before the run.
- YOLOX-Tiny's load time (77.8 s) includes importing the MobileCLIP tools; not its real load cost.
