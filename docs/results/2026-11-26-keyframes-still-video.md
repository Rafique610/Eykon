# Keyframes on long, mostly still video (EYKO-130)

26 November 2026. Head 4 question: "why keep your own frame selection?" On every
clip measured so far, evenly spaced frames found as many moments as ours (31 of 35
against 34, `2026-10-13-keyframes-slots-on-phone.md`), because those clips were short
and the camera never rested. A selective method can only win on video that is mostly
still with short events. This file tests exactly that.

## Written before any run

**Clips** (camera originals, recorded 14 October 2026, never run before; 500 MB copy limit removed in EYKO-122):

| Clip | File | Length | Place | Logged events |
|---|---|---|---|---|
| S3-01 | `PXL_20261014_103634515.mp4` | 5:15 | classroom desk | 8 |
| S3-04 | `PXL_20261014_105818478.mp4` | 4:48 | outside, standing | 5 |

The card names S3-01 and S3-02. S3-02 was never recorded; S3-04 (same kind: long clip, few
events) replaces it. S3-03 is sealed and stays unopened for the final run.

**Event windows.** The log sheet (`D:/eykon-cache/datasets/evals/clips/log.xlsx`, written by
a person on 14 October) gives one time per event. Each event becomes the window
[t − 2 s, t + 5 s]: 2 s for the logger's timing error, 5 s for the result of the event to be
in view. The scorer then widens every window by 1 s on each side (protocol section 4).
File: `docs/results/keyframes/moments-still-2026-11-26.csv` (13 events). Every second outside
a window counts as idle.

**Pass rule** (from the card): ours keeps a sharp frame in every logged event (13 of 13) **and**
keeps at most half the frames evenly spaced sampling needs to hit every event.

**Also reported:** frames kept in the idle stretches (should be near zero), frames dropped per
reason, evenly spaced frames at our count and at 1 per 3 s, codec keyframes, ffmpeg scene
filter, PySceneDetect. Phone cost on the Pixel 9 Pro XL: seconds of processing per minute of
video per stage, peak native memory, battery and temperature (phone unplugged). Three runs.

**Nothing is tuned on these clips.** The phone runs the app's current cut-offs.

## How this could be lying

Two clips, staged events, one person logging times by hand, one phone. A phone held still is
the best case for a "still" rule. Katna (EYKO-131) is not in the comparison.

## Results (run 26 November 2026, 9:44 to 10:11 PM, Pixel 9 Pro XL, Android 17)

Build: `feature/video-memory` 935d809 plus the EYKO-145 change (voice notes only; no video code
changed). Three runs per clip; all three kept exactly the same frames. Raw files:
`docs/results/keyframes/pixel9proxl-still-2026-11-26.json` (phone), `score-still-2026-11-26.md`
(laptop scorer output), `pixel-still-2026-11-26-eykonvideo.log` (the app's stage log),
`pixel-still-2026-11-26-instrument.txt` (`OK (1 test)`).

**Verdict: fails the pass rule, but ours beats every other method at the same frame count.**
It hits 10 of 13 events (the rule asked for 13), and on the outside clip it keeps more
frames than evenly spaced sampling needs.

### Both clips, same frame count as ours

| Method | Frames kept | Kept per minute | Events hit | Kept frames in idle time |
|---|---|---|---|---|
| **Ours (Pixel)** | 59 | 5.9 | **10 of 13 (77 %)** | 41 of 59 (69 %) |
| B0 evenly spaced, same count | 59 | 5.9 | 6 of 13 (46 %) | 51 of 59 (86 %) |
| B0 evenly spaced, 1 per 3 s (no budget) | 201 | 20.0 | 13 of 13 | 163 of 201 (81 %) |
| B1 codec keyframes (no budget) | 604 | 60.1 | 13 of 13 | 491 of 604 (81 %) |
| B2 ffmpeg scene filter | 59 | 5.9 | 5 of 13 (38 %) | 39 of 59 (66 %) |
| B3 PySceneDetect content | 59 | 5.9 | 7 of 13 (54 %) | 44 of 59 (75 %) |
| B3 PySceneDetect adaptive | 43 | 4.3 | 3 of 13 (23 %) | 29 of 43 (67 %) |

### Per clip, and the pass rule

| Clip | Ours: events hit / frames kept | Evenly spaced at our count | Fewest evenly spaced frames that hit every event | Pass rule |
|---|---|---|---|---|
| S3-01 classroom (5:15) | 5 of 8 with 7 | 1 of 8 | 30 | **fail** (3 events missed) |
| S3-04 outside (4:48) | 5 of 5 with 52 | 5 of 5 | 19 | **fail** (52 frames, rule allows at most 9) |

What this says:
- **Still room (S3-01): very selective, too selective.** 945 frames pulled, 7 kept (less sharp in
  its slot 840, still 84, repeats 14). At 7 frames ours finds 5 events and evenly spaced finds 1,
  but three events are lost: phone put on the desk (0:59), laptop opened (2:03; nearest kept frame
  129.7 s, 0.7 s past the window) and bottle placed (2:58). A small object added to an unchanged
  desk is dropped as a repeat or as "still". Which layer dropped each of the three was not
  checked in this run (the benchmark's database is in memory); `task frame-report` on a normal app
  run would show it.
- **Outside, camera held by hand (S3-04): finds everything, keeps far too much.** 865 pulled,
  52 kept (less sharp 768, still 14, repeats 31). Evenly spaced needs only 19 frames to hit all 5
  events. A moving hand-held view changes every frame, so the "still" and repeat layers have
  nothing to remove.
- Compared with October: on the short hand-held clips ours lost to evenly spaced at an equal
  budget (31 against 34 of 35). On long clips it wins at an equal budget (10 against 6 of 13).
  The selective layers pay off only when the view is still, and then they cut too hard.

### Phone cost (Pixel 9 Pro XL, median of 3 runs)

| Clip | Split (frames + sound) | Filter | Repeats (MobileCLIP) | Total | Seconds per video minute | Native memory |
|---|---|---|---|---|---|---|
| S3-01 | 115.9 s (frames 62-69 s, sound 47-50 s) | 3.4 s | 4.3 s (8 pictures) | 123.7 s (worst 123.8) | 23.6 | 199 MB |
| S3-04 | 81.0 s (frames 40-47 s, sound 27-41 s) | 3.7 s | 37.0 s (70 pictures, about 520 ms each) | 121.6 s (worst 131.8) | 25.3 | 199 MB |

Evenly spaced frames at our count cost 41-43 s (S3-01) and 29-44 s (S3-04) to decode on the
phone. Battery not reported: the phone was on the charger (level 52 % → 52 %); temperature
27.4 → 30.5 °C over the 27-minute run.

### Changes to the method during scoring

PySceneDetect's threshold search decoded the 1080p clips up to 13 times per detector and was still
on the first clip after an hour. It was stopped and re-run on 360 p copies of the clips
(`small_copy()` in `keyframe_eval.py`, cached in `D:/eykon-cache/bench/small-copies/`). Only the
two B3 rows used the copies; our frames, the other methods and the sharpness check used the
originals.

### Next

Not tuned here (the card forbids tuning on these clips). Two existing cards address the two
failures: EYKO-132 (compare a frame with recent frames, not the whole video, so a new object on
an unchanged desk is not dropped as a repeat) and EYKO-77 / 79 (cut-offs relative to the video).
Any change must be tuned on other clips and checked here once.
