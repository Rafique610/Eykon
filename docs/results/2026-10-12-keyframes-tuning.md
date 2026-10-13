# Keyframe comparison — tuning on the tuning clips

Run 12 October 2026, after the first run. Card EYKO-45, protocol step 5.
Tuning clips only (1, 2, 4, 5: 114 s, 26 moments). **The held-out clips (3, 6) were not opened and have not been used.**

> Moments: clips 1 and 2 checked by Rafique (no time changed); clips 4 and 5 are AI-marked only.

## Short version

**Tuning did not produce a win.** With the best settings found, our method finds the same
moments as evenly spaced frames, give or take one moment, at the same number of frames, and
it still runs the image model on nearly every frame, so it stays about ten times more
expensive on the phone. No setting was applied to the phone and no held-out run was made,
because there is no setting yet that deserves one.

## How the tuning was done

`src/benchmarks/keyframe_tune.py` is a laptop copy of the phone's layers, fed with the same
frames and the same exported MobileCLIP model, so hundreds of settings run in seconds.

How close the copy is to the phone, at the phone's own thresholds:

| Clip | Phone kept | Laptop copy kept | Same frames |
|---|---|---|---|
| 1 | 102 | 99 | 71 |
| 2 | 11 | 13 | 8 |
| 4 | 55 | 56 | 54 |
| 5 | 20 | 18 | 16 |

The totals are close; the exact frames differ (the two decoders pick slightly different
frames, and each decision depends on the ones before it). The copy is a guide for choosing
settings, not a replacement for the phone run.

## 1. Thresholds only (350 settings)

Fewest frames our method needs for each level of recall, and what the others reach with the
same number of frames per clip:

| Frames kept (per minute) | Ours | B0 uniform | B2 ffmpeg scene | B3 PySceneDetect content |
|---|---|---|---|---|
| 100 (53) | 26 of 26 | 26 | 19 | 23 with 75 |
| 75 (39) | 25 | 26 | 14 | 24 with 60 |
| 50 (26) | 23 | 25 | 13 | 21 with 43 |

B1 codec keyframes: 26 of 26 with 117 frames (cannot be set to a budget).
Below about 30 frames a minute ours falls off quickly (20 of 26 at 15 a minute).

**Uniform sampling is ahead of ours at every budget tried.** The scene-change tools are
well behind both.

## 2. One change to the method: compare only with recent frames

Our repeat layer compares each frame with every unique frame of the whole video. A marked
moment is a stretch of time, so when the camera returns to a view seen earlier, the whole
moment is dropped as a repeat. Comparing only with frames kept in the last W seconds:

| W | Similarity bar | Ours: moments / frames | Uniform, same frames |
|---|---|---|---|
| 3 s | 0.75 | 26 / 46 | 24 |
| 3 s | 0.65 | 26 / 39 | 25 |
| 3 s | 0.50 | 26 / 36 | 25 |
| 5 s | 0.80 | 26 / 42 | 25 |
| 5 s | 0.75 | 25 / 34 | 24 |
| 5 s | 0.65 | 25 / 27 | 25 |
| 5 s | 0.60 | 24 / 26 | 24 |
| 8 s | 0.80 | 22 / 33 | 23 |

With this change ours is level with uniform, sometimes one moment ahead, sometimes one
behind. One moment out of 26 is not a difference anyone should rely on. (The sweep also
produced a single setting with 26 moments from 27 frames; its neighbours score 24 and 25,
so it is luck, not a finding.)

The image model still ran on 340 of 345 frames at W = 5 s, so the phone cost would not drop.

## 3. No model at all

Keep a frame when the gray picture changed by at least D since the last kept frame (with or
without a "keep one every G seconds" rule). On these hand-held clips the picture changes so
much from frame to frame that it keeps far too many: 26 of 26 only with 54 or more frames,
no better than uniform.

## Why uniform is so hard to beat here

| Clip | Length | Moments | Share of the clip inside a (widened) moment |
|---|---|---|---|
| 1 | 65.7 s | 11 | 63 % |
| 2 | 12.4 s | 3 | 93 % |
| 4 | 21.7 s | 7 | 82 % |
| 5 | 14.3 s | 5 | 100 % |

Almost every second of these clips is inside a marked moment, the camera never rests, and
no frame is dark or badly blurred (7 of 198 frames in clip 1 are under half the clip's median
sharpness). In that situation evenly spaced frames are close to the best possible answer,
and a selective method has nothing to skip. Uniform alone, one rate for all four clips:
20 a minute finds 25 of 26, 25 a minute finds all 26.

A layered method can only show an advantage where most of the video is **not** worth
keeping: a phone left on a desk for minutes, with one short event such as keys being put
down. There, uniform either wastes frames on the unchanged scene or, at a low rate, misses
the short event. None of the six clips is like that. This is a statement about what the
data can show, not evidence that ours would win there.

## What I recommend

1. **Do not claim a win.** On this data: equal quality to uniform within one moment, about ten times the phone cost.
2. **Record the missing kind of clip**, which is also the project's real use case: 3 to 5 clips of 2 to 5 minutes, phone resting or propped up, mostly nothing happening, with two or three short events (an object put down, picked up, someone passing). Mark them under the same rules.
3. **Decide the recent-frames change on its merits.** For a memory app, coming back to a place later is a new moment, so comparing with the whole video is arguably the wrong rule regardless of scores. This is a design decision for Rafique, not a tuning result.
4. **Cut the model's cost before anything else**, because no threshold setting reduced model calls on hand-held video: run the model on fewer frames (for example one a second), try the smaller MobileCLIP-S0, and try the phone's faster execution settings. Each is a measured experiment.
5. **Keep the held-out clips sealed** until there is a setting chosen for a stated reason.

## How these numbers could be lying

- Four clips, 26 moments, 114 seconds. Differences of one or two moments are noise.
- More than 1,700 settings were tried on those 26 moments; the best of them will look better than it is.
- The laptop copy does not reproduce the phone frame for frame.
- Half the moments are AI-marked only; all were marked from frames 0.5 s apart.
- Giving uniform the same number of frames **per clip** as ours quietly tells it how busy each clip is, which a real fixed-rate sampler would not know.

## Files

- Tuning tool: `src/benchmarks/keyframe_tune.py` (`task tune-keyframes -- <onnx> <phone json> [<cache folder>]`)
- First run: `docs/results/2026-10-12-keyframes-first-run.md`
