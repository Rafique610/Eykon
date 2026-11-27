# Katna in the keyframe comparison (EYKO-131)

27 November 2026, laptop. The panel asked (12 Oct) for our keyframe selection to be compared
with existing tools. Four were run in October; Katna, which the protocol calls "the closest existing
tool to our idea, the most important comparison" (frame difference, brightness and contrast filter,
K-means on histograms, sharpest frame per cluster), was not. Measures and equal budget are fixed in
`docs/plans/keyframe-comparison-protocol.md`, section 4. Nothing was tuned.

## How it was run

- **Katna 0.9.2** (MIT, checked on its PyPI page 27 Nov), in a one-off environment, not added to
  `pyproject.toml`. Installed and ran on Python 3.10 with no error.
- `src/benchmarks/keyframe_katna.py`:

```
uv run --no-project --python 3.10 --with katna --with imageio-ffmpeg python src/benchmarks/keyframe_katna.py \
    <clips folder> <moments csv> <results json giving our frame count per clip>
```

- **Equal budget:** Katna is asked for exactly as many frames per clip as ours kept, and it keeps that many.
- Katna returns pictures without times; each picture is matched to the decoded frame it came from
  (smallest difference on a 64 x 36 grey copy).
- Clips above 720 p (S3-01, S3-04) are given to Katna as the same 360 p copy PySceneDetect used;
  scoring uses the original for every method.

## Results

| Data | Frames per method | Ours | Evenly spaced, same count | PySceneDetect content | **Katna** |
|---|---|---|---|---|---|
| Six short own clips (35 moments; ours = Pixel, 13 Oct) | 44 | 31 | 34 | 29 | **27** |
| S3-01 + S3-04, long and mostly still (13 events; ours = Pixel, 26 Nov) | 59 | 10 | 6 | 7 | **7** |
| EPIC-KITCHENS-100, 8 videos (158 moments by the dataset's annotators; ours = laptop copy with the slot rule) | 175 | 125 | 113 | – | **84** |

Raw tables: `docs/results/keyframes/katna-six-clips-2026-11-27.md`, `katna-still-2026-11-27.md`,
`katna-epic-2026-11-27.md`. Kept frames outside every moment: Katna 6 of 44, 43 of 59, 49 of 175.

**Verdict: Katna finds the fewest moments of all methods on every set.** It never beats ours,
and it beats evenly spaced frames nowhere.

Cost on the laptop: 7.5 s per video minute on the 360 p long clips, 10.8 on EPIC. On the six short
clips one value is not usable: the last clip (8.7 s) took hours (142,415 s per video minute in the
table), almost certainly Katna stuck on a very short video rather than working. Katna is Python +
OpenCV + scikit-learn and has no phone form; that is a statement about the tool, not a quality win.

## How this could be lying

- Katna was built for edited video; ours is continuous first-person video. That is the use case, but it
  explains part of the gap.
- EPIC "ours" is the laptop copy of the phone's layers, not the phone (on S3-01 the copy kept 3 of the
  Pixel's 7 frames, on S3-04 49 of 52); evenly spaced on EPIC at the same count found 113.
- Small sets: 35, 13 and 158 moments; on the 13-event set one event is 8 points.
