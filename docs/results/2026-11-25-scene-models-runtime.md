# EYKO-121: can the scene models run faster with the same output? (25–26 Nov 2026, interim)

Head 3 question E2. **Interim:** this file has the laptop timings for every model and setting, and a first look at how
far int8 moves the outputs. The card's real quality check (detections and captions identical on ≥ 95 % of frames) and
**static** int8 need a set of real frames (own50 and kit-clip frames, requested from Rafique on the card); they are not
done yet. Run: `src/benchmarks/model_runtime.py`; numbers: [`model-runtime/model-runtime.json`](model-runtime/model-runtime.json).

## Setup

- **The phone's five models** (`models/`, not in git): `yolox_tiny.onnx` (20.2 MB, the official release file),
  `dfine_s_obj365.onnx` (42.1 MB, the same Hugging Face file), `mobileclip_s2_image.onnx` (143 MB) and
  `mobileclip_s2_text.onnx` (254 MB), exported with the repo's scripts (the committed reference vectors came out
  unchanged), and `yoloe_11l_own.onnx` (110.7 MB), re-exported with today's Ultralytics and the app's six phrases
  (opset 18; output 1 × 42 × 8,400 as on the phone).
- **ONNX Runtime 1.31.1**, the version the app ships (`onnxruntime-android:1.31.1`), on the laptop's CPU (Intel
  i5-10310U, 4 cores / 8 threads). Inputs: the repo's 7 golden pictures (`detector_golden.jpg`, the 5 filter test
  pictures, `dog.jpg`) at each model's input size; the text model: the 10 golden sentences' tokens.
- 3 warm-up runs, then 20 timed runs per setting; median and 90th percentile. Repeats of the same setting agree within
  about 10 %, which is the noise here. One outlier: the text model's very first measurement (493 ms; the same setting
  measured again gave 60–66 ms, so the first was disturbed, most likely by loading the 254 MB file).
- **The app's setting:** 4 threads and full graph optimisation, except **D-FINE, which runs with graph optimisation off**
  ("onnxruntime-android 1.18 fails on this model's ScatterND node when the graph is optimised", `DfineDetector.kt`).

## Results (median ms per picture, laptop)

| Model | App setting | 1 thread | 2 | **4** | 8 | Optimisation off | basic | extended | all | **Dynamic int8** |
|---|---|---|---|---|---|---|---|---|---|---|
| YOLOX-Tiny | 34 | 79 | 48 | **35** | 39 | 50 | 48 | 45 | **35** | 148 (5.2 MB) |
| D-FINE S | 276 (opt. off) | 517 | 333 | **271** | 315 | **291** | 285 | 284 | 300 | 732 (11.3 MB) |
| YOLOE-11L | 930 | 1,591 | 1,027 | **806** | 1,063 | 1,368 | 1,560 | 1,448 | **1,019** | 5,939 (29.1 MB) |
| MobileCLIP-S2 image | 198 | 690 | 319 | 188 | **128** | 315 | 386 | 281 | **234** | 1,616 (36.8 MB) |
| MobileCLIP-S2 text | (493, disturbed) | 162 | 77 | **66** | 86 | 61 | 75 | 64 | **60** | 56 (64.0 MB) |

How far the output moved against the app's setting (largest absolute change; cosine for the 512-number vectors):

| Model | Other optimisation levels | Dynamic int8 (preview on the golden pictures) |
|---|---|---|
| YOLOX-Tiny | 0.00007 (no change) | up to 3.34 in the raw outputs |
| D-FINE S | **basic, extended, all: up to 4.75** (off = the app: 0) | up to 8.39 |
| YOLOE-11L | up to 0.033 | **up to 800**: the output is broken |
| MobileCLIP-S2 image | 0 | **lowest cosine −0.03**: the vectors no longer point the same way |
| MobileCLIP-S2 text | 0 | **lowest cosine 0.80** |

## What it shows

1. **The app's settings are already the fastest of these options** on the laptop: 4 threads is best or within noise for
   four of the five models, and full graph optimisation is the fastest level for YOLOX (1.4× faster than off), YOLOE
   (1.3×) and MobileCLIP image (1.3×). Only MobileCLIP image gains from 8 threads here (128 against 188 ms), but the
   laptop's 8 are 4 cores with two threads each; a phone's 8 cores are mixed big and small, so threads must be
   measured on the phone.
2. **D-FINE: the old workaround still matters.** On 1.31.1 the optimised graph no longer *fails*, but it **gives
   different outputs** (up to 4.75 in the raw scores and boxes) and is **not faster** (284–300 against 291 ms). Keep
   optimisation off: no speed to win, and a changed output.
3. **Dynamic int8 is out.** It is **2.6–8× slower** for the four vision models on this CPU, and it **breaks the
   outputs**: MobileCLIP image vectors turn by up to 90° (cosine −0.03), YOLOE's scores move by up to 800, the text
   vectors fall to cosine 0.80. Dynamic int8 quantises the weights of convolution layers, which ONNX Runtime runs slowly
   on x86 without the newest int8 instructions; the output damage does not depend on the CPU.
4. **What is left to try:** static int8 (weights *and* activations, tuned on 50 real frames), which usually suits
   convolution-heavy models (YOLOX, YOLOE) better, and phone-side options (XNNPACK, NNAPI), which are phone work.

## Static int8 on 300 COCO photos (added 26 Nov)

Own frames had not arrived, so COCO val2017 stands in: 300 photos (seed 121, `data/eyko121/coco/ids.txt`, not in git),
50 for calibration and **250 others for the check**. Each photo is shrunk to a 640-pixel longer side like the phone's
frames, then prepared and decoded with the app's own rules (`src/benchmarks/model_static_int8.py`: YOLOX top-left grey
letterbox in BGR 0–255, cut-off 0.35, NMS 0.45; D-FINE stretched to 640, cut-off 0.5, its "person" left out; YOLOE centred
letterbox, 0.25; MobileCLIP shorter side 256 + middle square; place and action share ≥ 0.30). Static int8: QDQ, per-channel
int8 weights, uint8 activations, MinMax calibration. Numbers: [`model-runtime/static-int8.json`](model-runtime/static-int8.json).

| Model | Float (app setting) | Static int8 | Same as today's app on 250 photos | Verdict |
|---|---|---|---|---|
| YOLOX-Tiny | 43 ms, 20.2 MB | 35 ms (1.23×), 5.3 MB | detections 42 %, people count 84 % | fails |
| D-FINE S | 322 ms, 42.1 MB | 227 ms (1.42×), 12.1 MB | detections **2.8 %** | fails badly |
| YOLOE-11L | 858 ms, 110.7 MB | 496 ms (**1.73×**), 29.0 MB | own things 87.6 % (only 31 photos had any) | fails 95 %, closest |
| MobileCLIP-S2 image | 123 ms, 143 MB | 161 ms (slower), 38.1 MB | median cosine 0.64 (lowest 0.31); place 50 %, action 61 % | fails |
| **Caption inputs** (objects, people, place, action) | | | **0.4 %** of photos identical | **far below 95 %** |

"Same detections": every detection has a partner with the same label and boxes overlapping ≥ 50 %, both ways.

**D-FINE control** (the optimiser alone also changes its raw outputs): float with optimisation off against on gives the
**same detections on 100 %** of the 250 photos; float-on against int8 gives 2.8 %. So int8 alone breaks D-FINE, and the
optimiser's raw changes (up to 4.75) never move a detection across the 0.5 cut-off. As far as COCO shows, the app could
switch D-FINE's optimisation back on; it was not faster on the laptop, so that only matters if it is faster on a phone.

**YOLOX** is opset 11; per-channel int8 needs opset 13, so it was converted first (float outputs identical, difference
0.0). A first run without the conversion failed to load YOLOX's int8 file, and its summary wrongly printed 0 %; fixed.

**Reading.** Plain static int8 makes the detectors 1.2–1.7× faster on this laptop and 3.5–4× smaller, but changes the
answers far too often, and MobileCLIP's vectors break. Timings in this run differ from the first one by up to 15 %
(D-FINE 322 against 276 ms float): laptop noise, the ratios hold.

**What could still work** (each its own piece of work): better calibration (percentile or entropy instead of MinMax),
keeping the most sensitive layers in float (mixed precision: the first and last layers, the detection heads, attention),
or training with quantisation in mind. YOLOE is the one worth it: the slowest stage (68 s a clip on the A32), the biggest
speed-up here (1.73×), and the closest to the bar (87.6 %, though on few finds). The real check needs our own frames.

## Limits

- Laptop timings, not phone timings; an ARM phone runs int8 with different kernels (so int8 *speed* may differ there;
  the output damage would not).
- 7 golden pictures (1–2 real camera frames); fine for speed, not a quality check.
- "Largest absolute change" on detectors is in raw output units (scores and box values), a first look only; the card's
  real check compares detections (label + IoU ≥ 0.5) and captions on real frames.

## Next

- Real frames from Rafique (own50, kit-clip frames): requested on EYKO-121.
- Then: the same check on our own frames (the card's real 95 % test, and YOLOE on frames that show keys and earbuds).
- If the owner wants it: mixed-precision int8 for YOLOE only.
