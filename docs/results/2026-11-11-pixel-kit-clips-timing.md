# EYKO-64: clean timing of the pipeline on the kit clips, and the cost of any-object crops, on the Pixel (Head 3, B1 and B2)

11 November 2026. Pixel 9 Pro XL (Android 17), on the charger the whole time, app in front, build `c5b919c` (app code of `feature/video-memory`). Two kit clips (`PXL_20261014_094359202`, 74.5 s, 186 MB; `PXL_20261014_094903187`, 75.0 s, 188 MB), each run twice. The repeat of a clip is the same clip with 8 empty bytes added at the end (a different fingerprint, so the duplicate check of EYKO-71 lets it in; the frames are identical). Tool: Zara's EYKO-117 harness (`run-head3.ps1`, branch `zara/eyko-117-head3-harness` at `fd935a9`), unmodified, run on a phone for the first time. The Pixel's own data was backed up first and put back afterwards (22 videos, files identical).

## Short answer

A minute of video costs the Pixel **0.88 minutes of work for clip 1 and 1.33 for clip 2**, with the app in front. The old figure on this phone was about 1.4 (20 Oct, old build, Ego4D). The Infinix needed 1.8 and 3.4 on the same clips, so the Pixel is **2.1 times and 2.6 times faster**. The any-object detector (YOLOE-11S prompt-free) would add about **36 s to clip 1 and 57 s to clip 2** (a 55 % and 57 % increase) and needs **1.1 GB of memory**; the decision for EYKO-62 is in the last section.

## Stage times on the Pixel (seconds)

| Run | Clip | Split frames | Split audio | Filter | Dedup | Scene | Small objects | Embed images | Embed texts | Latest | Total | s per s of video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | clip 2 | 26.6 | 6.2 | 0.6 | 9.7 | 8.1 | 16.7 | 0.0 | 0.5 | 34.1 | 102.7 | 1.37 |
| 4 | clip 2 | 26.6 | 7.2 | 0.6 | 3.4 | 7.9 | 17.0 | 0.0 | 0.2 | 33.8 | 96.6 | 1.29 |
| 2 | clip 1 | 26.6 | 6.2 | 0.6 | 2.5 | 4.9 | 11.0 | 0.0 | 0.2 | 12.4 | 64.5 | 0.87 |
| 3 | clip 1 | 27.4 | 6.0 | 0.6 | 2.4 | 4.9 | 11.3 | 0.0 | 0.1 | 12.6 | 65.2 | 0.88 |

Totals leave out the copy and the hash (they happen before the job starts). The two runs of a clip are within 0.7 s of each other for clip 1 and 6.1 s for clip 2; the 6 s is the first run of the session, where dedup took 9.7 s against 3.4 s later (a one-off model start-up cost, not tested on its own). Copy of a 186 to 188 MB clip: 947 to 1,099 ms, of which the hash was 123 to 136 ms (about 12 %).

## Pixel against the Infinix, same clips (medians for the Pixel, the single run of `2026-11-05-second-phone-first-run.md` for the Infinix)

| Stage | Clip 1 Pixel | Clip 1 Infinix | Clip 2 Pixel | Clip 2 Infinix |
|---|---|---|---|---|
| Split frames | 27.0 | 22.1 | 26.6 | 23.2 |
| Split audio | 6.1 | 13.8 | 6.7 | 13.7 |
| Filter | 0.6 | 1.4 | 0.6 | 1.4 |
| Dedup | 2.4 | 9.4 | 6.6 | 13.5 |
| Scene | 4.9 | 14.8 | 8.0 | 23.5 |
| Small objects | 11.2 | 31.0 | 16.9 | 44.6 |
| Embed texts | 0.1 | 0.4 | 0.4 | 0.4 |
| Latest | 12.5 | 42.3 | 33.9 | 136.5 |
| **Total** | **64.8** | **135** | **99.7** | **257** |
| Work per second of video | 0.87 | 1.8 | 1.33 | 3.4 |
| Kept frames, objects found | 10, 6 | 10, 6 | 16, 4 | 16, 4 |
| Sightings | 54 | 53 | 134 | 134 |

The two phones keep the same frames and find the same small objects; sightings differ by one on clip 1 (54 against 53). The Infinix ran the 4 Nov kit build, so this compares cost per minute of video, not an identical build.

What the table shows:
1. **Frame extraction is the one stage where the Pixel is slower** (26.6 to 27.4 s against 22.1 and 23.2 s) while its audio step is twice as fast. It is half of clip 1's time (33 of 65 s).
2. **`latest` grows with the number of sightings, in a straight line.** 12.5 s for 54 sightings and 33.9 s for 134 on the Pixel is 0.23 and 0.25 s per sighting; on the Infinix 0.80 and 1.02 s. That is the cost of one MobileCLIP crop vector per sighting, not a quadratic comparison. The odd result noted on 5 Nov (clip 2 taking 3.2 times longer) is the 2.5 times as many sightings. Faster `latest` has to mean fewer or cheaper crop vectors (for EYKO-120).
3. **Three stages are 80 % of the time:** split frames, `small_objects` and `latest`.

Heat and battery: the highest temperature was 34.3 to 36.7 C (30 C at the start); the battery stayed at 68 to 69 % because the phone was charging, so these runs say nothing about battery drain.

## Cost of any-object crops (YOLOE-11S prompt-free, AGPL-3.0, academic use only), on the Pixel

Method: the model exported from `yoloe-11s-seg-pf.pt` to ONNX at 640 x 640 (47.7 MB; output 4,621 numbers for each of 8,400 boxes, about 155 MB per frame); the 26 kept frames of the two runs (10 and 16) pulled from the phone and letterboxed on the laptop; `YoloePfPhoneBenchmarkTest` (ONNX Runtime, 4 threads, output read in place) timed the model run and the choice of the 10 surest boxes of at least 0.10 apart (the rule of EYKO-62). `src/benchmarks/yoloe_pf_phone.py`, results in `docs/results/eyko64/yoloe_pf_*`.

| Measure | Pixel | Laptop (ONNX, CPU) |
|---|---|---|
| Model run per frame | **1,039 ms median** (1,003 to 1,176) | 214 ms |
| Picking the 10 boxes | 127 ms median | not timed |
| Model load | 140 ms | not timed |
| Peak memory | **1,129 MB native heap, 1,131 MB PSS** | not measured |
| Boxes of at least 0.10 per frame | median 110, **identical to the laptop on all 26 frames** | the same |
| Crops per frame (10 surest) | 10 on every frame | 10 |

Calculated cost per clip (the detector part is measured; the crop vectors use the 0.23 to 0.25 s per sighting that `latest` measured above, so that part is an estimate):

| | Clip 1 (10 kept frames) | Clip 2 (16 kept frames) |
|---|---|---|
| Detector, 1.17 s per frame (run + pick) | 11.7 s | 18.7 s |
| 10 crop vectors per frame, 0.24 s each | 24 s | 38 s |
| **Added** | **about 36 s (+55 % on 65 s)** | **about 57 s (+57 % on 100 s)** |

Reading for EYKO-62: the quality gain (+11 points last-seen on held-out set B) costs roughly a 55 % longer job and 1.1 GB of working memory. That is more than YOLOE-11L's 570 MB native on the same phone (EYKO-84) and may not fit the 6 GB class of phone (the Samsung A32 was not tried). Cheaper options to test on the laptop first, none measured here: run it only on the frames the MobileCLIP gate flags (EYKO-63 did this for YOLOE-11L and cut its work to 15 to 20 % of frames), keep fewer than 10 crops per frame, or an int8 model. The licence stays AGPL and academic-only.

## Limits

- One phone, two clips, two runs each; a charging phone (no battery figure); the Infinix numbers are one run on an older build.
- The crop-vector part of the detector cost is calculated, not measured end to end; the detector was timed in a test process, not inside the job.
- Zara's harness added the copy and hash time to the processing total (about 1.2 s too much); the figures above leave them out. To be told to Zara (EYKO-117).
- Memory of the stages themselves was not sampled during the runs.
