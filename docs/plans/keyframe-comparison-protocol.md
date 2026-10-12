# Keyframe comparison — protocol (card EYKO-45)

> Written 12 October 2026, **before any method was run on the evaluation clips**.
> Status: **approved by Rafique on 12 October 2026** (method list, section 2; rules,
> section 4). The rules do not change after this; any later change is written in
> section 8 with its date and reason.

## 1. The question

The panel asked: is our layered way of choosing key frames (cheap filters, then
removing repeats) better than existing keyframe methods **on a mobile phone**?
Show the numbers, and tune ours to match or beat them.

Our method, as built on the phone (`android/.../video/`):

1. Pull frames at 3 per second.
2. Cheap filters (EYKO-5): too dark, too bright, blurry (variance of the Laplacian), unchanged since the last kept frame.
3. Repeats (EYKO-6): perceptual hash, then MobileCLIP similarity, each against every unique frame so far.

## 2. Methods to compare against (proposed)

Researched 12 October 2026. Licence and status are what the project pages said on
that day; each is re-checked when the method is installed.

| # | Method | What it does | Licence | Laptop | Phone |
|---|---|---|---|---|---|
| B0 | Uniform sampling | One frame every N seconds | none needed | yes | yes |
| B1 | Codec keyframes (I-frames) | Keeps the frames the video file already stores in full | none needed (part of the file format) | yes (ffmpeg) | yes (Android's own video reader) |
| B2 | ffmpeg scene filter | Keeps a frame when the picture changes by more than a set amount | LGPL / GPL (ffmpeg) | yes (already installed through `imageio-ffmpeg`) | **no maintained way**: FFmpegKit, the usual Android build, was retired and archived in 2025; only community forks remain |
| B3 | PySceneDetect (ContentDetector and AdaptiveDetector) | Finds cuts from colour change; we take the middle frame of each scene | BSD-3-Clause | yes | no (Python + OpenCV) |
| B4 | Katna | Frame difference, brightness and contrast filter, K-means on histograms, sharpest frame per cluster | MIT | yes, if it installs on our Python | no (Python + OpenCV) |

Notes:

- **B4 Katna is the closest existing tool to our idea** (difference, blur measure, grouping). It is the most important comparison.
- B2 on the phone: we do **not** add an unmaintained fork to the app. If wanted, the same idea (change in picture above a threshold) can be written in Kotlin and labelled honestly as "our port of the idea", not as the tool.
- **No learned keyframe model is on the list.** We found none that is small, maintained, permissively licensed and outputs key frames directly. Shot-boundary networks exist (for example TransNetV2) but they find cuts in edited video, which is not our case (one continuous phone recording).
- Optional outside reference, only if the panel wants it: the Open Video Project / VSUMM set (50 videos, five people's chosen key frames each). It is edited documentary footage, not phone video, so it would test generality, not our use case.

## 3. Data (Rafique records and marks)

- 10 to 15 clips recorded on the phone, 20 to 60 seconds each. At least two of each kind: an object put down or picked up; walking between rooms; a still scene; fast movement; poor light.
- Put the clips in `data/evals/keyframes/clips/` (this folder is not in git).
- Mark the key moments in `data/evals/keyframes/moments.csv`, one line per moment:

```
clip,start_s,end_s,what
kitchen_keys_01.mp4,7.0,9.5,keys put on the counter
kitchen_keys_01.mp4,21.0,23.0,keys picked up again
hall_walk_01.mp4,0.0,4.0,hallway
hall_walk_01.mp4,11.0,15.0,bedroom, bed and desk visible
```

- A moment is a stretch of time in which something worth remembering is visible. Mark them **before** looking at any method's output, by watching the clip in a normal player.
- A clip with nothing worth remembering has no lines; that is allowed and useful.
- Split, done once by file name order before any run: every third clip is **held out**; the rest are for tuning.

## 4. Measures (fixed here)

| Measure | Definition |
|---|---|
| **Moment recall** (main) | Share of marked moments that have at least one kept frame whose time is inside the moment, widened by 1 second on each side, **and** that frame is sharp |
| Sharp (for scoring only) | The frame's variance of the Laplacian (on the gray picture shrunk to about 320 px) is at least half the median of all frames of that clip at 3 per second. This is relative to the clip, so it does not depend on our own blur threshold |
| Frames kept per minute | Count of kept frames ÷ clip length |
| Wasted frames | Share of kept frames that fall inside no marked moment (± 1 s) |
| Phone cost | Seconds of processing per minute of video; peak memory; battery drop and highest temperature over a 10-minute run. Pixel 9 Pro XL and Samsung A32. Three runs: median and worst |

**Equal budget.** A method that keeps every frame has perfect recall, so methods are
compared at the same number of kept frames per clip: for each clip, every method is
set (by its own threshold or count setting) to keep as close as possible to the
number our method keeps, and the number it actually kept is reported beside its
recall. Where a method cannot be set (B1 codec keyframes), it is reported as it is
and marked as such. A second view plots recall against frames kept for each method.

## 5. Order of work

1. Rafique approves sections 2 and 4. This file is committed.
2. Rafique records and marks the clips (section 3).
3. Table 1, quality, on the laptop: every method on every clip, equal budget.
4. Table 2, cost, on both phones: ours, B0, B1 (and a Kotlin port of B2's idea, if approved).
5. Tune ours (thresholds, order of checks) on the tuning clips only.
6. Run once on the held-out clips. Those numbers are the result.
7. Results and limits go in `docs/results/`; the conclusion says where ours wins, ties or loses.

## 6. How these numbers could be lying

- Our clips, our rooms, one person marking; a second marker on a few clips would show how much people disagree.
- 10 to 15 clips is small: one moment can move a clip's recall a lot. Report counts, not only percentages.
- Equal budget hides that some methods cannot be set to a budget.
- A Kotlin port of an idea is not the tool it copies.
- Phone cost on a cool, idle phone is the best case.
- Laptop tools were not designed for phones; "cannot run on a phone" is a result about the tool, not a win on quality.

## 8. Changes after approval

**12 October 2026 — who marks the key moments, and what data there is.** Asked for by
Rafique to save time.

- **Marker.** Section 3 said Rafique marks the moments. Instead, an AI assistant (Claude)
  marked them, by looking at every clip as still frames taken twice a second, before any
  method had been run on the clips. Every line in `moments.csv` carries `marked_by = ai`.
- **Why this weakens the result, and the safeguard.** The same assistant builds and tunes
  our method, so it is not an independent judge, and it saw frames 0.5 s apart, not the
  moving video. Under the project's own rule (roadmap section 5.1) an automatic judge must
  be cross-checked by a person: **Rafique checks the marks of at least two clips against
  the video** (agree / missing / wrong, counted), and that count is reported beside the
  results. Until then every number from this comparison is labelled "AI-marked, not yet
  checked by a person".
- **Data actually provided.** Six clips, 138 s in total (8.7 s to 65.7 s), in
  `data/evals/keyframes/clips/` (folder name as created; section 3 said `eval`). They were
  shared through WhatsApp, so they are re-compressed to about 480 x 640 and are not the
  camera's original files. Scenes: a classroom desk, a cafeteria table, a corridor, a
  computer lab, a terrace, a road. 35 marked moments. This is below the 10 to 15 clips the
  protocol asked for; more clips can be added later under the same rules.
- **Split.** By file-name order, every third clip is held out: clips 3 and 6 (9 moments).
  Clips 1, 2, 4 and 5 (26 moments) are for tuning.
- **Where the marks live.** `data/evals/keyframes/moments.csv` (not in git, with the
  clips), and a copy committed as `docs/results/keyframes/moments-2026-10-12.csv` so the
  record shows they existed before any result.
- **People in the clips.** The clips show classmates and passers-by. They stay on this
  laptop and the test phones, are never committed or uploaded, and are described in the
  marks only by clothing.

## 7. What we already know (before the comparison)

From one real 3-second pan clip on the Pixel 9 Pro XL (12 October 2026, not part of the evaluation set):
9 frames pulled, filters kept 9, hash dropped 0, MobileCLIP dropped 2. Blur scores were 721 to 1,397
against a threshold of 60, and the closest two frames differed by 11 of 64 hash bits against a
threshold of 6, so on hand-held video neither cheap layer did anything and the model (281 ms per
frame, about 63 % of the processing time) ran on every frame. Both thresholds are expected to need tuning.
