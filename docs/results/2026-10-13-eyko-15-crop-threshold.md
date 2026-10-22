# EYKO-15: when are two sightings the same object? (13 October 2026)

**In one line:** comparing the objects' own crops with MobileCLIP separates "same object" from
"different object" only partly: the two groups overlap between 0.77 and 0.92. The threshold is
set to 0.87, where 15 of 48 same-object pairs are missed and 3 of 288 different-object pairs are
merged. The same-object pairs available were the easy kind, so real use will be worse.

## What was run

- Phone: Google Pixel 9 Pro XL. `ObjectCropBenchmarkTest` put the six evaluation clips through
  the app's stages up to the scene records and saved every detected object's own crop (the
  square around its box) with its MobileCLIP vector: 90 crops, none too small, 567 ms per crop.
- Identity: `latest/crop-identity-2026-10-13.csv`. The AI assistant looked at the 90 crops and
  grouped the ones that clearly show the same physical thing: 54 crops, 24 things. The other 36
  were left out as unclear. **Not checked by a person.**
- Pairs (`task crop-pairs`, `src/benchmarks/crop_pairs.py`): only between crops with the same
  detector name and from different frames, because that is all the stage ever compares.
  Vectors: `latest/pixel9proxl-object-crops-2026-10-13.json`.
- The rule for choosing was fixed first: the threshold with the fewest wrong calls over both lists.

## Result

| Pairs | How many | Lowest | Quarter below | Middle | Three quarters below | Highest |
|---|---|---|---|---|---|---|
| Same object | 48 | 0.766 | 0.854 | 0.908 | 0.940 | 0.974 |
| Different objects, same name | 288 | 0.470 | 0.658 | 0.740 | 0.797 | 0.917 |

| Threshold | Same pairs called different | Different pairs called same |
|---|---|---|
| 0.75 | 0 of 48 | 133 of 288 |
| 0.80 | 1 of 48 | 65 of 288 |
| 0.85 | 9 of 48 | 12 of 288 |
| **0.87 (chosen)** | **15 of 48** | **3 of 288** |
| 0.90 | 20 of 48 | 2 of 288 |

Fewest wrong calls (18 of 336) at 0.86 and 0.87; 0.87 is `VideoLatest.CROP_COSINE_MIN`.

Pairs by detector name (same, different): dining table 22 and 54, chair 14 and 210, laptop 6
and 8, monitor ("tv") 3 and 7, cell phone 2 and 8, "suitcase" 1 and 1.

- 14 of the 15 missed same-object pairs are "dining table". Its boxes cover most of the frame,
  so the crop is the whole scene and changes as the camera moves; it is not really an object crop.
- The 3 merged pairs: two neighbouring cafeteria tables, and one person's two knees, which the
  detector had called "chair" (0.90 and 0.92).

## What a wrong call does

- Same object called different: both sightings stay "latest", so "where is it now" shows the
  old place as well as the new one.
- Different objects called the same: the older one is marked replaced and drops out of "now".

## How this could be lying

- **Every same-object pair is from one clip, seconds apart, in one place.** The card asks for
  the same object on another day or in another room, which we do not have. Those pairs would
  score lower, so more than 15 of 48 would be missed in real use.
- Many "different" pairs are unlike things that share a wrong name (a knee and a chair, both
  "chair"). They are easy to tell apart, which makes the different group look better separated
  than two real chairs would be.
- 54 crops, six clips, one marker, no second check.
- The objects are whatever YOLOX-Tiny named, right or wrong. Keys and other small things are
  not in it (card EYKO-32 is parked).

## Found while checking the app's own videos

Sighting times were first stored as written by the clock ("...:28Z" but "...:28.333Z"). Sorted
as text that puts 28.333 before 28.0, so newer and older were mixed up and one laptop had two
"latest" sightings. Times are now always stored with three decimals; a test covers it. After
the fix the seven videos in the app have 26 sightings and 6 latest ones, one per object.

## Cost

One MobileCLIP run per object: about 540 ms each on the Pixel. A 22 s clip with 8 kept frames
and 28 objects took 15.0 s in this stage, more than all the earlier stages together.
