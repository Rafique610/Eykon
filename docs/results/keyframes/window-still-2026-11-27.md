## Does the laptop copy keep the phone's frames? (whole video, phone cut-offs)

| Clip | Phone kept | Copy kept | Same second (within 0.05 s) |
|---|---|---|---|
| PXL_20261014_103634515.mp4 | 7 | 6 | 3 |
| PXL_20261014_105818478.mp4 | 52 | 52 | 49 |

## Repeats against the whole video or the last W seconds (2 clips, 13 moments)

| Rule | Frames kept | Moments hit | Recall | Kept frames outside every moment | MobileCLIP runs |
|---|---|---|---|---|---|
| whole video (the app today) | 58 | 9 of 13 | 69.2% | 42 | 74 |
| last 5 s only | 84 | 12 of 13 | 92.3% | 63 | 94 |
| last 10 s only | 76 | 11 of 13 | 84.6% | 56 | 86 |
| last 30 s only | 66 | 10 of 13 | 76.9% | 47 | 78 |
| last 60 s only | 63 | 10 of 13 | 76.9% | 46 | 76 |

### per clip (moments hit / frames kept)

| Clip | whole video (the app today) | last 5 s only | last 10 s only | last 30 s only | last 60 s only |
|---|---|---|---|---|---|
| PXL_20261014_103634515.mp4 | 4/8 with 6 | 7/8 with 18 | 6/8 with 14 | 5/8 with 10 | 5/8 with 8 |
| PXL_20261014_105818478.mp4 | 5/5 with 52 | 5/5 with 66 | 5/5 with 62 | 5/5 with 56 | 5/5 with 55 |
