# Keyframe comparison — outside data (EPIC-KITCHENS-100), untuned

Run 13 October 2026 on the laptop. Card EYKO-45. Nothing was tuned on these videos: "ours" is
the laptop copy of the phone's layers at the phone's own thresholds (`keyframe_tune.py`).
**Not yet run on a phone.**

## Short version

On video marked by other people, the result is the same as on our own clips: **evenly spaced
frames find as many moments as our method, with the same number of frames, and need no image
model.** Ours is well ahead of the scene-change tools and of codec keyframes.

## Data

- Source: EPIC-KITCHENS-100 (University of Bristol), head-mounted camera in home kitchens.
  Licence CC BY-NC 4.0 (non-commercial, credit required). Videos from `data.bris.ac.uk`,
  annotations from `github.com/epic-kitchens/epic-kitchens-100-annotations`.
- Moments: the dataset's own action segments (start and end time, for example "pick up glass"),
  marked by its annotators. 158 moments. Neither the project nor the AI assistant marked them.
- Eight videos, 11 minutes in total, chosen by a rule fixed before any method ran
  (`selection.csv`): length 45 to 120 s, at least 8 actions, 1920x1080, one per participant.
  - **sparse**: the four with the smallest share of time inside an action (31 to 39 %).
  - **typical**: the four closest to the median share (67 %).
- Shrunk to 640x360, 30 frames a second (65 MB in total); the 2.4 GB originals were deleted.
- Everything is in `D:\eykon-cache\datasets\epic100\` (not in git).

## Results (all eight videos)

| Method | Frames kept | Per minute | Moments hit | Wasted frames |
|---|---|---|---|---|
| Ours (laptop copy, phone thresholds) | 900 | 81.6 | 151 of 158 (96 %) | 26 % |
| B0 uniform, same count per video | 900 | 81.6 | 153 of 158 (97 %) | 30 % |
| B0 uniform, 1 a second | 663 | 60.1 | 154 of 158 (97 %) | 33 % |
| B0 uniform, 1 every 2 seconds | 331 | 30.0 | 145 of 158 (92 %) | 33 % |
| B3 PySceneDetect content | 592 | 53.7 | 131 of 158 (83 %) | 34 % |
| B2 ffmpeg scene filter | 900 | 81.6 | 127 of 158 (80 %) | 20 % |
| B1 codec keyframes (no budget) | 110 | 10.0 | 55 of 158 (35 %) | 31 % |

By group, moments hit:

| Method | sparse (85 moments) | typical (73 moments) |
|---|---|---|
| Ours | 78 with 370 frames | 73 with 530 |
| Uniform, same count | 80 with 370 | 73 with 530 |
| Uniform, 1 a second | 82 with 326 | 72 with 337 |
| Uniform, 1 every 2 seconds | 75 with 162 | 70 with 169 |

The image model ran on 1,352 frames to keep 900.

## What this says

1. Uniform at one frame a second finds more moments than ours with a quarter fewer frames, even on the "sparse" videos.
2. Ours wastes slightly fewer frames than uniform at the same count (26 % against 30 %), a small effect.
3. At the phone's thresholds ours keeps about 82 frames a minute. That is far too many; the layers drop little on head-camera video, as on our own clips.
4. Scene-change tools and codec keyframes are clearly worse on continuous video. That part of the claim holds on outside data.

## How these numbers could be lying

- Laptop copy, not the phone. It does not match the phone frame for frame.
- Eight videos, one dataset, kitchens only, head-mounted camera (not a phone left on a desk).
- "Sparse" here still means over 30 % of the time is inside an action, and scoring widens each moment by 1 s. No video is mostly empty.
- EPIC actions are short and dense (about 14 a minute). A method that keeps many frames is rewarded; recall alone does not punish keeping too many.
- The videos were re-encoded when shrunk, so "codec keyframes" are those of our re-encode, not the camera's.
- The marks are of actions. They are not a list of what a user would later ask about.

## Run it

```
task eval-keyframes-public -- D:/eykon-cache/datasets/epic100/clips D:/eykon-cache/datasets/epic100/moments.csv D:/eykon-cache/models/mobileclip_s2_image.onnx D:/eykon-cache/datasets/epic100/cache D:/eykon-cache/datasets/epic100/selection.csv
```

## Trial: motion-paced keyframes (13 October 2026, laptop, no image model)

Idea: a stretch of video ends when the summed frame-to-frame change passes a budget, or after a
maximum gap; keep the sharpest frame of each stretch. Tool: `src/benchmarks/keyframe_motion.py`.
Split fixed before the trial: within each group, by name, the first two videos are for tuning
(P02_119, P07_13, P03_06, P04_14) and the last two are held out (P26_11, P30_01, P11_24, P16_02).
Two settings were chosen on the tuning videos, then run **once** on the held-out videos.

Moments found, at the same total number of frames:

| Videos | Setting (budget : max gap) | Frames (per minute) | Motion-paced | Evenly spaced | Evenly spaced, sharpest of each slot |
|---|---|---|---|---|---|
| Tuning, 72 moments | 200 : 12 | 110 (19) | 66 | 57 | 59 |
| Tuning, 72 moments | 300 : 18 | 75 (13) | 58 | 44 | 50 |
| **Held out, 86 moments** | 200 : 12 | 124 (24) | **72** | 69 | **81** |
| **Held out, 86 moments** | 300 : 18 | 84 (16) | **60** | 59 | 59 |
| Our own tuning clips, 26 moments | 200 : 12 | 54 (28) | 25 | 25 | 25 |
| Our own tuning clips, 26 moments | 300 : 18 | 37 (19) | 24 | 26 | 25 |

**Reading.** The lead on the tuning videos (9 and 14 moments) did not survive: on the held-out
videos motion pacing is 3 and 1 moments ahead of evenly spaced frames, and at one setting it is
9 behind "evenly spaced, sharpest of each slot". Motion pacing is not a reliable gain.
Picking the sharpest frame inside each slot was never worse than plain even spacing by more
than one moment and once much better; that is the old blur layer used as a chooser, not a filter.

**What does hold.** How many frames are kept matters far more than which rule picks them. At about
20 frames a minute, any of these three finds roughly 80 to 95 % of the moments with no image
model in the selection step, where the current layers run the model on nearly all 180 frames a minute.

Limits: 86 held-out moments, one dataset; two settings picked from 48 on the tuning videos;
the held-out videos are now used and cannot serve as a clean test again.
