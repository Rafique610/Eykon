# EYKO-117: Head 3 intake harness on the Infinix X670 (14 Nov 2026)

Phone: Infinix X670, Android 13, MT6781V. App build on the phone: `zara/eyko-44-workmanager` at 5a192c7 (WorkManager foreground worker; it also has EYKO-71's `copy` log line and duplicate refusal). Harness: `docs/phone-kit/run-head3.ps1` at 3317e65 plus the `--runs` chart option, one command per run, serial as argument. The app was in front for every run; the app was reset to empty between runs (the app refuses a second copy of the same bytes).
The phone was on a USB cable (charging) for every run, so **`battery_used_pct` is not battery use** (the run notes say so). Temperatures are the battery temperature.
Kit clips (2): clip 1 `PXL_20261014_094359202.mp4` (186,496,580 bytes, 74.5 s) and clip 2 `PXL_20261014_094903187.mp4` (187,772,438 bytes, 74.9 s).
**Run numbers:** S1 runs 1-3 are clip 1, runs 4-6 are clip 2 (so the CSVs do not mix them).
Files: `docs/results/head3/stage_times.csv`, `run_summary.csv`, `raw/` (Eykon log lines, battery.csv, device sheet per run), charts `stage_medians_S1_clip1.png` and `stage_medians_S1_clip2.png`.
How clips were added: S1 by Zara through the photo picker. S2 and S3 through the same picker, driven by adb with Zara's permission, limited to Eykon, the picker and its Movies album (one clip per add, about 2 min apart).

## S1: each kit clip alone (3 runs each)

| Clip | Run | Video | Stage time added up | Work per video second | Copy | Battery % | Highest temp |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 74.5 s | 141.0 s | 1.89 | 1,171 ms | 59 to 59 | 31.2 C |
| 1 | 2 | 74.5 s | 138.0 s | 1.85 | 795 ms | 59 to 58 | 32.7 C |
| 1 | 3 | 74.5 s | 134.1 s | 1.80 | 429 ms | 58 to 58 | 34.6 C |
| 2 | 4 | 74.9 s | 225.9 s | 3.02 | 1,003 ms | 58 to 57 | 34.6 C |
| 2 | 5 | 74.9 s | 235.7 s | 3.15 | 613 ms | 57 to 57 | 36.0 C |
| 2 | 6 | 74.9 s | 241.1 s | 3.22 | 895 ms | 57 to 56 | 37.2 C |

The spread inside a clip is small (clip 1: 134-141 s, clip 2: 226-241 s, about 3-5%). The spread between the clips is large.

Median seconds per stage (copy and hash happen before the job starts and are not in the totals):

| Stage | Clip 1 (runs 1-3) | Clip 2 (runs 4-6) | S2 (10 videos) | S3 (clip 2) |
|---|---|---|---|---|
| copy | 0.8 | 0.9 | 1.6 | 1.0 |
| hash | 0.2 | 0.2 | 0.3 | 0.2 |
| split (frames) | 21.7 | 22.0 | 20.8 | 20.9 |
| split (audio) | 9.1 | 11.3 | 10.8 | 12.0 |
| filter | 2.1 | 1.8 | 1.4 | 1.6 |
| dedup | 10.5 | 14.3 | 11.2 | 14.2 |
| scene | 17.0 | 25.8 | 19.7 | 24.4 |
| small_objects | 32.1 | 45.7 | 41.8 | 44.4 |
| embed_images | 0.0 | 0.0 | 0.0 | 0.0 |
| embed_texts | 1.6 | 1.4 | 0.3 | 1.3 |
| **latest** | **44.0** | **111.1** | **81.0** | **113.2** |

**Which stage takes the time (B1):** `latest` by far: 44 s of 141 s on clip 1 (31%) and 111 s of 226 s on clip 2 (49%). After it come `small_objects` (32-46 s), `scene` (17-26 s) and the split (about 31 s). Copy, hash, filter, embed_images and embed_texts together are under 8 s.
**Why clip 2 costs more:** it keeps more frames and finds more things. After dedup clip 1 keeps 10 frames and clip 2 keeps 16; `latest` finds 53 sightings on clip 1 and 134 on clip 2. Cost per unit is the same on both: `latest` about 0.83 s per sighting, `scene` about 1.7 s per frame. So the difference is the footage, not heat. (Clip 2's runs also came later and warmer, 34.6-37.2 C against 31.2-34.6 C, so heat is not fully excluded, but the per-unit figures match.)

## S2: queue of ten

10 videos, 5 of each kit clip (each clip and four copies with 1-4 empty `free` atoms appended, so the bytes differ: 187,772,438 / 446 / 454 / 462 / 470 and 186,496,580 / 588 / 596 / 604 / 612). All 10 reached ready, 0 unfinished.

| | |
|---|---|
| Video in the queue | 747.0 s (10 videos) |
| Stage time added up | 1,918.0 s (32.0 min) |
| Work per video second | 2.57 |
| Wall time, first split to last finish | 1,920 s |
| Copy per video | 704 / 1,668 / 1,193 / 1,548 / 1,567 / 1,626 / 1,780 / 1,733 / 1,545 / 1,635 ms |
| Battery / highest temp | 56 to 53 % (charging, so not battery use) / 38.6 C |

The queue ran one video after another with the app in front, with no failures. The 10 files were added about 2 minutes apart (one add at a time through the picker), so the queue was never empty while a video was processing. Copy times were higher than in the single runs (median 1.6 s against 0.8-0.9 s), probably because the previous video was being processed at the same time; that was not tested.

## S3: copy time

The largest kit clip, 187,772,438 bytes: **966 ms** to copy (hash 221 ms inside it), from the app's own `copy` log line. Across all single-video runs the copy took 429-1,171 ms, under 1% of the 134-241 s of processing. **Once EYKO-126 lands (no more copy), this S3 figure is the "before" number.**

## S4: back-fill

Video `1a02b0c9...` (finished, from S3): its saved stage was set to `latest` in `memories.db` (WAL checkpointed first, all three files kept as `.before-backfill` in `raw/`), the app was force-stopped and reopened. Only **`finish`** ran again. No other stage ran. This is Rafique's clean control. `finish` writes no time to the log, so S4 has no stage time (0.0 s in `run_summary.csv`).

## Reruns and limits

- No stage ran twice within one log (`rerun` is empty for every row).
- Battery use per minute of video (B3) is **not answered** by these runs: the phone was charging over USB throughout. Heat is: 27-38.6 C battery temperature over the session.
- S4 was run once; the card asks for one back-fill check.
- The harness and parser ran on a Pixel too (Rafique, `docs/results/eyko64/`); these are the Infinix figures.
- Build caveat: this build includes the WorkManager change (EYKO-44), not a build from before it.
