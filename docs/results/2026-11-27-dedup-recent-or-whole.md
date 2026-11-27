# Drop repeats against the whole video or only recent frames? (EYKO-132)

27 November 2026. On the 26 Nov still-video test (EYKO-130) the classroom clip lost three
events (phone put down, laptop opened, bottle placed): the filter passed 21 frames and the
repeat layer cut them to 7, because each frame is compared with every unique frame of the whole
video, so a small new object on an unchanged desk looks like a repeat. For a memory app a
return to a place is also a new moment. This file measures the other rule.

## Written before any run (approved by Rafique, 27 Nov: "i approve")

**Change measured:** `VideoDedup` compares a frame only with unique frames kept in the last
W seconds. Nothing else changes: hash at most 6 bits, MobileCLIP cosine at least 0.95, the same
filter and slot rule. The app keeps the whole-video rule (`VideoDedup.WHOLE_VIDEO`); the window
is a parameter used only by the benchmark.

**Where:** on the laptop (Rafique, 27 Nov: "the recent-frames test on the laptop"), with
`src/benchmarks/keyframe_window.py`: a copy of today's phone layers. `keyframe_tune.py`'s copy
predates the 3-second slot rule, so the new script adds it, and first prints how many of the
Pixel's 26 Nov kept frames the copy keeps too. The phone benchmark ("windowed" section of
`KeyframeBenchmarkTest`) is ready as well and runs if the rule passes, before any app change.
W = 5, 10, 30 and 60 s are reported, as the card asks.

**The decision uses W = 30 s only**, fixed before the run. Adopt "recent frames" for the app if
all hold:
1. Long still clips (S3-01, S3-04): at least 12 of the 13 logged events, with at most 59 frames
   kept (today's count).
2. EPIC-KITCHENS-100 (8 videos, 158 moments by the dataset's annotators, never used for tuning):
   moment recall within 1 point of the whole-video rule on the same phone run.

Otherwise the whole-video rule stays and the 26 Nov numbers are the final Head 4 result.
W = 5, 10 and 60 are shown for the record and do not decide anything.

The card's variant (c) "whole video, but a repeat is allowed again after W seconds" is the same
rule as (b): a frame older than W no longer counts as a match either way.

**Card step 1** (which 5 frames MobileCLIP dropped on 13 Oct, and whether they were the 3
missed moments) cannot be answered from saved data: the 13 Oct phone file keeps only the kept
times and the drop counts, not the dropped frames' times.

## Results (laptop, 27 November 2026)

Command (features cached in `D:/eykon-cache/bench/window-cache/`):

```
uv run --with scenedetect --with onnxruntime python src/benchmarks/keyframe_window.py \
    D:/eykon-cache/models/mobileclip_s2_image.onnx <clips folder> <moments csv> [<phone json>]
```

Raw output: `docs/results/keyframes/window-still-2026-11-27.md`, `window-epic-2026-11-27.md`.

**Verdict: fails the pass rule. The whole-video rule stays in the app; nothing is ported.**
At W = 30 s the long clips give 10 of 13 events with 66 frames (the rule asked for at least 12
with at most 59). EPIC passes its half (79.1 % against 79.1 %), but both halves were required.

### How close is the laptop copy to the phone? (whole video, against the Pixel's 26 Nov run)

| Clip | Pixel kept | Copy kept | Same second (within 0.05 s) |
|---|---|---|---|
| S3-01 classroom | 7 | 6 | 3 |
| S3-04 outside | 52 | 52 | 49 |

Close on the hand-held clip, loose on the still one: with only a handful of frames left, a small
difference in decoding or JPEG coding changes which frame of a slot is sharpest. The copy finds
9 of 13 events where the Pixel found 10. So compare rules **within** the copy, as below; do not
mix its numbers with the phone's.

### Long, mostly still clips (13 events)

| Rule | Frames kept | Events hit | Kept outside every event | MobileCLIP runs |
|---|---|---|---|---|
| Whole video (the app today) | 58 | 9 | 42 | 74 |
| Last 5 s only | 84 | 12 | 63 | 94 |
| Last 10 s only | 76 | 11 | 56 | 86 |
| **Last 30 s only (the decision)** | **66** | **10** | 47 | 78 |
| Last 60 s only | 63 | 10 | 46 | 76 |

| Clip | Whole video | 5 s | 10 s | 30 s | 60 s |
|---|---|---|---|---|---|
| S3-01 classroom (8 events) | 4 with 6 | 7 with 18 | 6 with 14 | 5 with 10 | 5 with 8 |
| S3-04 outside (5 events) | 5 with 52 | 5 with 66 | 5 with 62 | 5 with 56 | 5 with 55 |

### EPIC-KITCHENS-100 (8 videos, 158 moments by the dataset's annotators)

| Rule | Frames kept | Moments hit | Recall | Kept outside every moment |
|---|---|---|---|---|
| Whole video | 175 | 125 | 79.1 % | 58 |
| Last 5 s | 180 | 126 | 79.7 % | 63 |
| Last 10 s | 177 | 125 | 79.1 % | 60 |
| **Last 30 s** | **175** | **125** | **79.1 %** | 58 |
| Last 60 s | 175 | 125 | 79.1 % | 58 |

### What it means
- The diagnosis was right: on the still classroom clip, comparing with recent frames only brings
  missed events back (4 → 7 of 8 at 5 s). But it brings them back by keeping more frames, at the
  same rate evenly spaced sampling would: 5 s needs 18 frames for 7 events; evenly spaced needed
  30 for all 8 on the phone run.
- On the hand-held clip and on EPIC the window changes almost nothing: there the camera moves,
  so frames rarely repeat anything older than a few seconds anyway.
- W = 5 s reaches 12 of 13, but with 84 frames (over the 59 limit), and it was not the setting
  chosen before the run; it is reported, not adopted.
- So the honest Head 4 statement stays: our selection is cheaper than evenly spaced frames at
  close recall, not better. Making it keep small changes on a still desk costs frames, not cleverness.

The window parameter written for the phone benchmark was removed again (the rule failed, so no
app code changes). The phone benchmark was not run for this card.
