# Ego4D baseline: the app's pipeline as built (EYKO-55, EYKO-56)

20 October 2026. The first outside score of what Eykon does today, before any change.
Clips: the 24 Ego4D episodic-memory validation clips of `2026-10-19-ego4d-subset.md`.

## How it was run

- **Accuracy on the laptop:** `task ego4d-pipeline` (`src/benchmarks/ego4d_pipeline.py`) runs the phone's stages with the phone's ONNX files and constants:
  - 3 fps frames and 9-frame slots
  - filters, dHash and MobileCLIP dedup
  - YOLOX-Tiny + D-FINE S + YOLOE-11L
  - MobileCLIP place and action prompts
  - the caption rule, object crops

  All 24 clips (177 min) took **46.4 min** with 4 clips at a time. They kept 1,878 frames.
- **Scoring:** `task ego4d-eval` (`src/benchmarks/ego4d_eval.py`). The rules are written at the top of that file and were fixed before any score was read. Numbers: `docs/results/ego4d/baseline-2026-10-20.json`.
- **Phone check:** 4 of the clips (27.8 min) went through the real app on the Pixel 9 Pro XL (section below).

## Objects: "where did I put X?" (NLQ Objects + Place templates, 78 questions)

The question goes through the app's search (MobileCLIP text vector against every kept frame).

| Measure | Ours | Random kept frame |
|---|---|---|
| R@1, tIoU ≥ 0.3 | 10.3 % | |
| R@1, tIoU ≥ 0.5 | 6.4 % | |
| R@5, tIoU ≥ 0.3 | 19.2 % | |
| R@5, tIoU ≥ 0.5 | 10.3 % | |
| hit@1 (top frame inside the answer window ±1.5 s) | **24.4 %** | 3.4 % |
| hit@5 | **47.4 %** | |

## People (NLQ People template, 12 questions)

R@1 0 %, R@5 at tIoU ≥ 0.3 8.3 %. hit@1 8.3 % against a random kept frame's 5.2 %; hit@5 33.3 %. The search does not tell people apart: there are no faces and no names.

## Objects: "when did I last see this?" (VQ, 39 queries)

The query photo's crop is embedded with MobileCLIP and compared with the app's object crops in kept frames before the query moment. The answer is the latest crop with cosine ≥ 0.87, the app's own same-object rule.

| Measure | Ours |
|---|---|
| success (answer frame inside the response track ±1.5 s) | **33.3 %** |
| seen (the object was ever cropped by our detectors, cosine ≥ 0.87, inside the track) | 12.8 % |

Success is higher than seen because, when nothing reaches 0.87, the most alike crop is used, and it sometimes lands in the track. So most hits do not come from the same-object rule.

## Actions, social, mobility (MQ, our 8 prompts)

| Area | Ego4D class | Ours | Instances | found | R@1 tIoU ≥ 0.5 |
|---|---|---|---|---|---|
| social | converse / interact | talking to someone | 8 | 25 % | 0 % |
| actions | read | reading | 5 | 0 % | 0 % |
| mobility | walk up / down stairs | walking | 4 | 100 % | 25 % |
| actions | use a laptop | typing on a laptop | 2 | 100 % | 0 % |
| actions | stir before cooking | cooking | 2 | 50 % | 0 % |
| actions | use phone | not covered | 23 | | |
| actions | drink beverage | not covered | 3 | | |
| actions | cut / chop food | not covered | 3 | | |

Precision: the share of frames labelled with an action that fall inside a true segment of a matching class.

| Action | Frames | Precision |
|---|---|---|
| talking to someone | 57 | 35.1 % |
| walking | 62 | 8.1 % |
| typing on a laptop | 28 | 3.6 % |
| cooking | 77 | 2.6 % |
| reading | 89 | 0 % |
| eating | 49 | 0 % |

"Picking something up" (256 frames) and "putting something down" (83) have no matching MQ class here, so they are not scored. They are also the two labels given most often.

## Published numbers, for scale only

These come from different splits, metrics and query sets, so they are not a ranking.

| Task | Method | Score |
|---|---|---|
| NLQ (test, all templates) | OSGNet 2025 | R@1 0.3 / 0.5: 28.50 / 20.05; R@5: 46.00 / 32.97 |
| NLQ (test, all templates) | EgoVideo 2024 | R@1: 25.07 / 17.31 |
| VQ2D (test) | RELOCATE | Success 60.1, stAP25 0.35 |
| VQ2D (test) | VQLoC | Success 55.9 |
| MQ (test) | OSGNet 2025 | mAP 35.31 |

Those run large video models on GPUs. Ours runs per-frame models that fit a phone.

## On the phone (EYKO-56)

4 clips (27.8 min: three of 8 min, one of 3.8 min) added through the app's own picker on the Pixel 9 Pro XL, 20 October. The phone was on the charger, so no battery figure. Compared with `task ego4d-phone-compare`.

**Does the laptop copy match the app?**

| Clip | Kept, phone / laptop | Same second | Same place | Same action | Same people count | Object names overlap | Same caption |
|---|---|---|---|---|---|---|---|
| 57c09157 (8 min) | 156 / 155 | 151 | 148 | 144 | 113 | 0.78 | 57 |
| f21ba0cf (8 min) | 69 / 72 | 66 | 66 | 66 | 60 | 0.85 | 41 |
| c7873f07 (8 min) | 113 / 113 | 103 | 103 | 97 | 100 | 0.81 | 61 |
| ffc52dc7 (3.8 min) | 34 / 35 | 34 | 34 | 33 | 33 | 0.87 | 19 |
| **All** | **372 / 375** | **354** | **351 (99 %)** | **340 (96 %)** | **306 (86 %)** | **0.78–0.87** | **178 (50 %)** |

- Frame choice, place and action carry over almost exactly, so the NLQ and MQ scores above are the app's.
- Objects differ at the edges. The phone's hardware decoder and the laptop's FFmpeg give slightly different pixels, so detector scores move by up to about 0.1. Objects close to a cut-off (D-FINE 0.5, YOLOX 0.35) then appear on one side only, which changes about half the captions by one word. VQ uses object crops, so its score carries this uncertainty.

**Cost on the phone**

| Measure | Value |
|---|---|
| Processing time | 27.6 min for 20.0 min of video (the 3 clips run without interruption), **about 1.4 min per minute**. For an 8-minute clip that keeps 156 frames: 13.4 min, of which YOLOE alone is 6.4 min (2.5 s a frame). The f21ba0cf clip took 21.2 min because it stalled while another app was in front. |
| Caption text | 19.0 KB for 27.8 min, **0.7 KB per minute** (CapMem's VLM captions: 3.6–5 KB per minute) |
| Database growth | about 7 MB (4.3 MB backup before, 11.3 MB after), with every vector |
| Frame JPEGs | 244 MB, **8.8 MB per minute**. Dropped frames' JPEGs are kept on disk (VideoFilter keeps the file), and they are most of this. |
| Each video's folder | 530 MB in all, with the app's copy of the video and the 16 kHz WAV |
| Phone temperature | 28.0 °C → 36.4 °C |

The frame files are the storage problem, not the memory itself. Deleting dropped frames' JPEGs would keep only the kept ones (372 of about 4,200).

## What this says

1. **Search finds the right moment more often than it pins its edges.** The top frame is inside the answer 24 % of the time (7x a random frame), but its 3 s window rarely overlaps enough (6.4 % at 0.5). Joining frames into longer windows, which is the CapMem / OSGNet way, is the next measured change.
2. **"Last seen" depends on the detectors cropping the object.** Only 12.8 % of queried objects were ever cropped. Ego4D asks about any object; our detectors name COCO / Objects365 things and two own words.
3. **Actions are the weakest area, as expected.** Per-frame prompts work only for talking (35 % precision) and walking past stairs. Reading, eating and cooking labels are mostly wrong. "Use phone" (the largest class here) has no prompt. This is the evidence for EYKO-52 (better prompts) and EYKO-25 (a clip model).
4. **People** need faces (EYKO-27). Today the search cannot tell one person from another.

## Limits

- The sample is small (78 + 12 NLQ, 39 VQ, 50 MQ instances from 7 videos). These numbers give a direction, not a final score.
- These are validation clips, scored with our own scripts, not the Ego4D server.
- Social covers only the conversation class. The AV / social benchmarks need other downloads.
- The laptop copy is not the app itself. EYKO-56 compares the two on 4 clips.
