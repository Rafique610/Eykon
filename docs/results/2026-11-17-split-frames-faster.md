# Split frames faster with the same JPEGs (commit d93c56b, 15 Nov), and the A32 after it (17 Nov)

Head 3 question B1 (which stage takes the time). Until this file the change was recorded only in the commit, its test and the
15 Nov day log; this is its result file.

**Why.** On the Pixel 9 Pro XL `split_frames` was the largest single stage of kit clip 1 (26.7 of 63.9 s, EYKO-123,
`2026-11-15-head3-intake-two-phones.md`), and the one stage where the Pixel was slower than the Infinix.
**Change (d93c56b).** `FrameExtractor.toJpeg` copies pixel rows in bulk instead of one pixel at a time, and the decoder is asked to
run at full speed (`MediaFormat.KEY_OPERATING_RATE` set to the maximum). Nothing about which frames are taken or how they are encoded changed.
**How it is measured.** `SplitTimingBenchmarkTest` (on-device, measurement only): kit clip 1 (`PXL_20261014_094359202.mp4`, 74.5 s,
224 frames) pushed to `files/eval_clips/kit1.mp4`, three runs, each split into decoding, conversion to JPEG and writing, plus one
SHA-256 over every JPEG in frame order. Run with `adb shell am instrument -w -e class com.eykon.memory.video.SplitTimingBenchmarkTest
com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner`; result lines in logcat, tag `EykonVideo`, "split timing".

## Results (kit clip 1, 224 frames, three runs)

| Phone, build | Whole split | Decoding | To JPEG | Write | JPEG hash |
|---|---|---|---|---|---|
| Pixel 9 Pro XL, before (15 Nov, working tree before d93c56b) | 28.8-32.2 s | 18.6-19.6 s | 9.0-13.3 s | 0.3 s | `5866f9ce1066ef4f` |
| Pixel 9 Pro XL, after d93c56b (15 Nov) | **7.9-10.4 s** | not kept | not kept | not kept | `5866f9ce1066ef4f` |
| Samsung A32, after (17 Nov, e4f2bd7) | **24.0-26.4 s** | 21.4-22.4 s | 2.1-3.5 s | 0.4-0.5 s | `5866f9ce1066ef4f` |

A32 raw lines: `split-timing/a32-2026-11-17-e4f2bd7.txt`. The Pixel figures are from the 15 Nov session (`.memory/15-november-2026/tasks.md`,
row 10); its raw logcat was not saved, which is the weakness of this row.

## Reading

1. **Same output.** The hash of all 224 JPEGs is identical before and after on the Pixel, and identical on the A32: the two phones' decoders
   and our encoder write the same bytes for this clip.
2. **Pixel: about 3x faster** (28.8-32.2 s to 7.9-10.4 s). Before the change, JPEG conversion was 9-13 s of it; full-speed decoding took most of the rest.
3. **A32: decoding is 89 % of the split** (21.4-22.4 of 24.0-26.4 s). JPEG conversion is only 2.1-3.5 s, so the bulk copy already does its job
   there; what is left is the A32's video decoder. A faster split on the A32 would have to decode fewer frames, which changes the output.
4. The A32 was not measured before d93c56b, so its gain is not known.

## Limits

- One clip (1080p HEVC, 20 Mbps). The Infinix was not run with this test.
- The Pixel "after" breakdown (decoding / JPEG / write) was not kept, only the totals and the hash.
- This is the split stage in a test process, not inside a job: the stage time in a job also includes the audio track and database writes.
