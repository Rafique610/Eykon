
### tuning clips (1, 2)

| Method | Frames kept | Kept per minute | Moments hit | Moment recall | Wasted frames |
|---|---|---|---|---|---|
| ours (Google Pixel 9 Pro XL) | 59 | 5.9 | 10 of 13 | 77% | 41 of 59 (69%) |
| B0 uniform | 59 | 5.9 | 6 of 13 | 46% | 51 of 59 (86%) |
| B0 uniform, 1 per 3 s (no budget) | 201 | 20.0 | 13 of 13 | 100% | 163 of 201 (81%) |
| B1 codec keyframes (no budget) | 604 | 60.1 | 13 of 13 | 100% | 491 of 604 (81%) |
| B2 ffmpeg scene filter | 59 | 5.9 | 5 of 13 | 38% | 39 of 59 (66%) |
| B3 PySceneDetect content | 59 | 5.9 | 7 of 13 | 54% | 44 of 59 (75%) |
| B3 PySceneDetect adaptive | 43 | 4.3 | 3 of 13 | 23% | 29 of 43 (67%) |

### all clips (1, 2)

| Method | Frames kept | Kept per minute | Moments hit | Moment recall | Wasted frames |
|---|---|---|---|---|---|
| ours (Google Pixel 9 Pro XL) | 59 | 5.9 | 10 of 13 | 77% | 41 of 59 (69%) |
| B0 uniform | 59 | 5.9 | 6 of 13 | 46% | 51 of 59 (86%) |
| B0 uniform, 1 per 3 s (no budget) | 201 | 20.0 | 13 of 13 | 100% | 163 of 201 (81%) |
| B1 codec keyframes (no budget) | 604 | 60.1 | 13 of 13 | 100% | 491 of 604 (81%) |
| B2 ffmpeg scene filter | 59 | 5.9 | 5 of 13 | 38% | 39 of 59 (66%) |
| B3 PySceneDetect content | 59 | 5.9 | 7 of 13 | 54% | 44 of 59 (75%) |
| B3 PySceneDetect adaptive | 43 | 4.3 | 3 of 13 | 23% | 29 of 43 (67%) |

### per clip (moments hit / frames kept)

| Method | clip 1 | clip 2 |
|---|---|---|
| ours (Google Pixel 9 Pro XL) | 5/8 with 7 | 5/5 with 52 |
| B0 uniform | 1/8 with 7 | 5/5 with 52 |
| B0 uniform, 1 per 3 s (no budget) | 8/8 with 105 | 5/5 with 96 |
| B1 codec keyframes (no budget) | 8/8 with 315 | 5/5 with 289 |
| B2 ffmpeg scene filter | 2/8 with 7 | 3/5 with 52 |
| B3 PySceneDetect content | 4/8 with 8 | 3/5 with 51 |
| B3 PySceneDetect adaptive | 0/8 with 1 | 3/5 with 42 |

### frames each needs to hit every moment

| Clip | Ours kept | Fewest evenly spaced frames that hit every moment |
|---|---|---|
| clip 1 | 7 | 30 |
| clip 2 | 52 | 19 |
