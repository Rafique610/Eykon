# EYKO-32: where to look for a small named object — hands or grid? (13 October 2026)

**In one line:** on head-camera kitchen video, cropping around hands found by MediaPipe almost
never names the handled object (at most 6 of 44 events); cutting the frame into 18 tiles finds
it in 20 to 33 of 44 depending on how strict the minimum is, but names several other objects per
frame and costs 18 MobileCLIP runs. Neither is good enough to build as it stands.

A laptop measurement to choose the approach before building on the phone. Nothing was built into
the app. Run with `task eval-small-objects`; raw output in `small-objects/epic-2026-10-13.json`.

## What was run

- **Data:** the eight EPIC-KITCHENS-100 videos already on disk (640x360 copies, CC BY-NC 4.0),
  with the dataset's own labels, made by people. No new clips were recorded.
- **Objects:** every object class with at least 3 take / put events in those videos, except
  "food": glass, pan, plate, spoon, bowl, spatula, knife, chopping board, box. **These are kitchen
  things, not keys, wallet or glasses.** The mechanism is tested, not the user's own objects.
- **Frames:** 44 event frames (the middle of each take / put of a listed object) and 94
  no-object frames (the middle of every other action with no listed event within 1 s).
- **Naming a crop:** the card's rule. MobileCLIP-S2 shares over "a photo of <object>" for the
  nine objects plus "an empty hand" and "something else"; the top phrase counts only when it is a
  listed object with a share of at least the minimum.
- **Where it looks:** hand crops from MediaPipe Hands (Apache-2.0, `hand_landmarker.task`) at
  1.5, 2 and 3 times the hand's size; grids of 3 and 18 overlapping square tiles; the whole frame.
- Object list, frames, scoring and the tuning / held-out split were fixed from the labels before
  any model saw a frame. The frames were then looked at by eye to check that labels and video
  line up (they do).

## Result 1: the hand finder misses most hands

| Hand finder setting | Event frames with a hand found |
|---|---|
| MediaPipe Hands, default confidence 0.5 | 12 of 44 |
| Confidence 0.1 and the frame enlarged twice (added after seeing the first row) | 20 of 44 |

In the frames checked by eye a hand is clearly in view in most events (holding a plate, a pan
handle, a spatula). MediaPipe also put "hands" on a plate and on a cupboard door. It was built
for hands facing a camera, not for the back of the wearer's own hands seen from above.
It took 15 ms per frame on the laptop.

## Result 2: how often the handled object is named

All 44 event frames. "Names per frame" is how many different objects a frame gets on average
over all 138 frames; "x chance" compares with naming that many of the nine objects at random
(1.0x is no better than guessing).

| Where it looks | Crops per frame | Min 0.30: found, names, x chance | Min 0.90: found, names, x chance |
|---|---|---|---|
| Whole frame | 1 | 12 of 44, 0.75, 3.3x | 5 of 44, 0.16, 6.4x |
| Grid, 3 tiles | 3 | 15 of 44, 1.25, 2.4x | 8 of 44, 0.30, 5.5x |
| Grid, 18 tiles | 18 | 33 of 44, 4.27, 1.6x | 20 of 44, 1.15, 3.6x |
| Grid, 3 + 18 tiles | 21 | 33 of 44, 4.36, 1.5x | 20 of 44, 1.20, 3.4x |
| Hands, crop 2 x hand | 0.5 | 2 of 44, 0.22, 1.8x | 1 of 44, 0.04, 4.7x |
| Hands, crop 3 x hand | 0.5 | 3 of 44, 0.26, 2.4x | 1 of 44, 0.04, 5.6x |
| Eager hands, crop 3 x hand | 0.7 | 6 of 44, 0.38, 3.2x | 1 of 44, 0.07, 2.8x |
| Hands 2 x, plus the whole frame | 1.5 | 13 of 44, 0.86, 3.1x | 6 of 44, 0.18, 6.8x |

This table was added after the first scoring (below) was seen, and says so in the script. It
uses no "false alarm" label, which is why it is the fairer of the two.

## Result 3: the scoring fixed in advance

Settings picked on four videos, reported on the other four (20 events, 54 no-object frames).

| Where it looks | Minimum picked | Found | "False alarms" | Precision |
|---|---|---|---|---|
| Whole frame | 0.55 | 3 of 20 | 19 of 54 | 0.10 |
| Grid, 3 tiles | 0.95 | 3 of 20 | 6 of 54 | 0.23 |
| Grid, 18 tiles | 0.95 | 6 of 20 | 27 of 54 | 0.13 |
| Grid, 3 + 18 tiles | 0.95 | 7 of 20 | 27 of 54 | 0.14 |
| Hands, crop 2 x hand | 0.85 | 1 of 20 | 1 of 54 | 0.17 |
| Eager hands, crop 3 x hand | 0.30 | 3 of 20 | 15 of 54 | 0.12 |

How this could be lying: a kitchen worktop shows plates, glasses and knives in most frames
whether or not anyone touches them. A method that correctly names a glass standing on the
counter is charged a "false alarm" here, and the tuning then pushes the minimum up to 0.95 and
throws away real finds. So precision and false alarms in this table are too harsh on the grid.
"Found" is sound. By object on the held-out frames, the 18-tile grid found glass 3 of 5,
plate 1 of 3, chopping board 1 of 3, box 1 of 1, and no spoon (0 of 2), bowl (0 of 4) or
knife (0 of 2); it said "box" 19 times when no box was the labelled object.

## What it means

- **Card option 1 (MediaPipe hands) does not work on head-camera video.** The hand finder is the
  failure, not the idea: with no hand found there is nothing to crop.
- **Card option 3 (grid) finds far more, as the user expected,** but it is not precise. To
  find three quarters of the events it names about four of the nine objects in every frame.
- **Cost of the grid on the phone (estimate, not measured):** 18 tiles are 18 MobileCLIP runs.
  At the 281 to 544 ms per picture measured on the Pixel in EYKO-6, that is roughly 5 to 10 s per
  kept frame, against 0.24 s for the detector.
- **The naming rule is part of the problem.** "Something else" almost never wins against nine
  concrete object phrases, so every crop is forced towards some object.

## Limits

- 44 events, eight videos, one dataset; kitchens, and kitchen objects rather than keys.
- 640x360 copies of the videos; the originals were deleted after the keyframe work.
- One frame per event (the middle of the labelled span). An object missed there may be clear a
  moment earlier or later.
- The eager hand setting and Result 2 were added after the first results were seen.
- These eight videos were already used for the keyframe trials.
- No phone run: times on the phone are estimates from earlier measurements.
