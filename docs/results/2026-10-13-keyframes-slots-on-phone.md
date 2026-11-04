# Keyframes — slot picking on the phone

Run 13 October 2026 on the Pixel 9 Pro XL (over wireless debugging), card EYKO-45.
The filter stage now takes frames in 3-second slots and keeps at most the sharpest frame of each
(`FrameFilters.pickSlot`, `SLOT_FRAMES = 9`); MobileCLIP then drops repeats among those only.
Same six clips and 35 marked moments as the first run. This run includes the held-out clips
(3 and 6), so they are now used.

## Phone cost, seconds of processing per minute of video (median of 3 runs)

| | Pull frames | Filter | Repeats (MobileCLIP) | Total | Frames kept of 416 |
|---|---|---|---|---|---|
| Before (every frame checked on its own) | 21.3 | 1.4 | 114.7 | 137.5 | 227 |
| Now (sharpest of each 3 s slot) | 19.1 | 1.0 | 12.4 | **32.6** | 44 |

About 4 times less work. Native memory is unchanged (about 322 MB, the model). Pulling the
frames is now the largest part. For scale, the first run measured evenly spaced frames with no
model at 13.4 s per minute.

## Moments found (scored on the laptop, equal number of frames)

| Method | Frames kept | Tuning clips (26) | Held-out clips (9) | All (35) |
|---|---|---|---|---|
| Ours, now | 44 | 24 | 7 | 31 |
| B0 uniform | 44 | 26 | 8 | 34 |
| B3 PySceneDetect content | 45 | 22 | 7 | 29 |
| B3 PySceneDetect adaptive | 44 | 12 | 8 | 20 |
| B2 ffmpeg scene filter | 44 | 11 | 2 | 13 |
| B1 codec keyframes (no budget) | 142 | 26 | 9 | 35 |
| Ours, before (first run) | 227 | | | 34 |

## Reading

- The cost fell from 137.5 to 32.6 s per minute of video; frames kept fell from 227 to 44.
- That cost 3 moments (34 to 31 of 35).
- Evenly spaced frames at the same count found 34. **Ours is 3 moments behind uniform here**, and ahead of the scene-change tools.
- Of the 372 dropped frames, 367 were "less sharp" in their slot and 5 were repeats found by the model. Whether those 5 account for the missed moments was not checked.

## Limits

35 moments, six short clips, 16 of the moments AI-marked only; one phone; a cool, idle phone;
3 moments is within noise for this much data. The slot length (3 s) was not tuned.

Raw phone file: `docs/results/keyframes/pixel9proxl-slots-2026-10-13.json`.
