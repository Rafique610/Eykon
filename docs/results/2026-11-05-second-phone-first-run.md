# Second phone, first run: the video pipeline on an Infinix X670 (EYKO-84, gap G13)

5 November 2026. Run by Zara Tahir on her own phone. First run of the video pipeline on a phone other
than the Pixel 9 Pro XL. Raw files are in `docs/results/second-phone/` (see "Evidence files" at the end,
including what is not raw).

## Phone (device sheet)

| Item | Value |
|---|---|
| Maker, model | INFINIX, Infinix X670 |
| Chip (`ro.soc.model`) | MT6781V/CDZAMB-H |
| RAM (`MemTotal`) | 7,931,676 kB (about 7.6 GiB) |
| Android | 13 (the app needs 12 or newer) |
| Storage before the run | 110 GB total, 99 GB used, 11 GB free |
| Kit | phone kit 2026-11-03, built from commit `a637e1d` (`KIT-VERSION.txt`); all 10 files passed `sha256sum -c` |
| App before the run | `com.eykon.memory` 1.0, installed 2026-10-02, with a 12 KB `memories.db` and 3.4 GB of old files in the models folder (Gemma, its cache, Whisper tiny). No ONNX models. |

Phone was charging over USB for the whole session (battery 97 to 99 %). Free memory at the start was low
(`MemFree` 312 MB, `MemAvailable` 2.9 GB).

## What was done

1. Backed up the old `memories.db` and its WAL (kept outside the repo).
2. `adb install -r` of `app-debug.apk` and `app-debug-androidTest.apk`. Both "Success"; the app opened.
3. `push-models.bat`: six ONNX models, 703 MB (703,156,997 bytes), next to the old files.
4. Pushed the two kit clips to `/sdcard/Movies/` and rescanned. They did not show at the top of the picker
   (it lists newest first, they are dated 14 October); found by scrolling down.
5. Added the clips through the app's Video tab, app in front, screen on. First a Snapchat clip as a
   smoke test (not part of this result), then `PXL_20261014_094359202.mp4`, then
   `PXL_20261014_094903187.mp4`.
6. No `connectedDebugAndroidTest` was run.

## Result

**Both kit clips went through every stage and reached `ready`. No crash, no out-of-memory. The phone is
not too weak for the pipeline.**

### Per-stage times (logcat tag `EykonVideo`)

| Stage | PXL ...094359202 (`008a56...`) | PXL ...094903187 (`e30e08...`) |
|---|---|---|
| Frames from the video / audio length | 224 frames, 74.5 s | 225 frames, 74.9 s |
| split (frames) | 22.1 s | 23.2 s |
| split (audio) | 13.8 s | 13.7 s |
| filter | 1.4 s, kept 25 of 224 | 1.4 s, kept 25 of 225 |
| dedup | 9.4 s, kept 10 of 25 (hash dropped 14, embedding dropped 1) | 13.5 s, kept 16 of 25 (hash dropped 9, embedding dropped 0) |
| scene (option A) | 14.8 s, 10 frames, 1,476 ms each | 23.5 s, 16 frames, 1,466 ms each |
| small_objects | 31.0 s, 6 found | 44.6 s, 4 found |
| embed_images | 2 ms (10 reused) | 4 ms (16 reused) |
| embed_texts | 0.4 s, 10 captions | 0.4 s, 16 captions |
| latest | 42.3 s, 53 sightings (0 boxes too small) | **136.5 s**, 134 sightings (2 boxes too small) |
| Sum of the logged stage times | about 135 s | about 257 s (4 min 17 s) |
| Sum per second of video | about 1.8 | about 3.4 |
| Final line | `finish ... ready; 214 dropped frame files deleted` | `finish ... ready; 209 dropped frame files deleted` |

The sums add the audio time to the split time and treat the stages as running one after another. The
per-second figures divide by the audio length. They are estimates from the log, not a stopwatch.

Odd: both clips are about 75 s, but `latest` took 3.2 times longer on the second one, with 134 sightings
against 53. It may be the content of the clip. Not investigated.

### Memory, temperature, battery

| Reading | Value | Source |
|---|---|---|
| Native memory at `dedup` (the log's own figure) | 1,078 MB (clip 1), 1,075 MB (clip 2); Snapchat 338 MB | log line |
| Peak resident memory (`VmHWM`) | **1,152,504 kB (about 1.10 GiB)**, over all three runs in one process | `/proc/28196/status` |
| Resident memory after the runs (`VmRSS`) | 607,564 kB | same |
| Swap in use (`VmSwap`) | 318,788 kB | same |
| PSS idle, before clip 2 | about 790-797 MB | 10:22:42 to 10:23:44 samples |
| PSS highest sample during clip 2 | 863,154 kB at 10:24:00 | `clip2-readings` |
| Temperature | 29.8 C before processing; 33.5 to 33.9 C during clip 2; 33.7 C between the clips | `dumpsys battery` |
| Battery | 97 % at the start, 98 % between the clips, 99 % during clip 2 (charging) | same |

Limits of these numbers:

- The sampling loop for clip 2 started at 10:22:42 and stopped at 10:25:02. Clip 2 ran until 10:28:11, so
  the last part of `small_objects` and the whole `latest` stage (136 s) were not sampled. 863 MB is the
  highest sample, not a proven peak. `VmHWM` is the real peak (resident memory, a different measure from
  PSS, so the two are not comparable).
- Nothing was sampled during clip 1 or the Snapchat run (temperature and PSS for those runs are not
  recorded). `VmHWM` covers them.
- The phone was charging, so battery drain could not be measured.

### Storage after the three runs

| Part | Before | After |
|---|---|---|
| Private app data (`du -sk .`) | 217 KB | 380,230 KB (about 371 MiB) |
| `files/videos` (the app keeps a full copy of each video) | not measured | 378,390 KB |
| `databases` (db, WAL, shm) | not measured (`memories.db` was 12 KB) | 1,812 KB; `memories.db` is 1,294,336 bytes |
| Frame files kept separately | not measured | none (`files/` holds only `videos` and a 4 KB `profileInstalled`) |
| Shared app folder (`/sdcard/Android/data/...`) | 3.2 GB (before the model push) | 3.8 GB (the six ONNX files are 703 MB of that) |

About 2.7 minutes of video in total (11.5 s + 74.5 s + 74.9 s) added about 371 MiB of private data, almost
all of it video copies (about 141 MiB per minute of video). The two PXL files are 374.3 MB; the `videos`
folder is about 13 MiB larger, probably the Snapchat clip's copy (not checked). The database grew by about
1.6 MiB (about 0.6 MiB per minute, rough, includes the WAL). This is the first storage point for EYKO-96.

### Search checks in the app (typed into the app by hand; screenshots in `screenshots/`)

The app's library ("Saved videos (3)") holds 30 frames in total:

| Library entry | Frames kept | Which file |
|---|---|---|
| 14 Oct 2026, 14:45, 75 s | 10 | `PXL_20261014_094359202.mp4` |
| 14 Oct 2026, 14:50, 75 s | 16 | `PXL_20261014_094903187.mp4` |
| 17 Oct 2026, 13:42, 12 s | 4 | the Snapchat smoke-test clip |

(The mapping is by frames kept, which matches the log. The app shows the recording time, not the file name.)

| Query | What the app returned | Time |
|---|---|---|
| "where did i put my keys?" | closest 16 frames, best first | **2,193 ms** (first search after the app started) |
| the same query, repeated twice (the keyboard typed a capital "I") | closest 16 frames again | 161 ms and 227 ms |
| "how many pens were seen in the video?" | closest 14 frames, best first | 145 ms |

- **Cold start:** the first search was about ten times slower than the repeats of the same query. That
  fits a one-off load of the text model, but it was not verified.
- **Answers are frames, not numbers.** The pens question returned a list of frames, each with its time
  range, its stored caption and a "likeness" score. It did not return a count.
- **Scores:** keys 0.261 down to 0.093 (16 frames); pens 0.223 down to 0.111 (14 frames).
- **Frames from the 17 Oct Snapchat clip:** 3 of the 16 for keys (0.162, 0.121, 0.093) and 3 of the 14
  for pens (0.204, 0.176, 0.111). The smoke-test clip is still in the library and still gets searched.
- **Matching (read by eye from the screenshots by the assistant who captured them; the tester should
  confirm):** keys, visible on the table in about the first 3 of 16 frames (the 14:45 clip, with the
  phone and a blue pen beside them); a pen, visible in the first 2 of 14 frames (also the 14:45 desk
  frames). The remaining frames show a wallet, earbuds, glasses, empty chairs or the 17 Oct classroom.
  Both queries rank mostly the same desk frames at the top, because the keys and the pen lie together.

## Comparison with the Pixel 9 Pro XL (cost reference, not the same clips)

The Pixel's only video-pipeline numbers are the lead's 20 Oct run on four Ego4D clips (27.8 min):
`docs/results/2026-10-20-ego4d-baseline.md`, section "On the phone (EYKO-56)". Ego4D clips cannot be
shared and the tester has no Ego4D licence, so they were not run on the Infinix. The Pixel run also used
the 20 Oct app build, before later stage changes (the Infinix run used the 4 Nov kit build `a637e1d`).
This table therefore compares **cost per minute of video only**. It is not a same-clip parity check.

| Measure | Infinix X670 (PXL clips, 4 Nov build) | Pixel 9 Pro XL (Ego4D clips, 20 Oct build) |
|---|---|---|
| Video length | 74.5 s and 74.9 s | 27.8 min (three of 8 min, one of 3.8 min) |
| Work per minute of video | about 1.8 and 3.4 min | about 1.4 min (27.6 min for 20.0 min of video) |
| YOLOE per frame (`small_objects`) | 3.1 s and 2.8 s | 2.5 s |
| Phone temperature | 29.8 to 33.9 C (sampled, charging) | 28.0 to 36.4 C (on the charger) |
| Database growth | about 1.6 MiB for 2.7 min (about 0.6 MiB/min, rough) | about 7 MB for 27.8 min (about 0.25 MB/min) |
| Video copies | about 141 MiB per minute (full copy of phone clips at about 2.5 MB/s) | 530 MB for 27.8 min with the WAV (lower-bitrate clips). Not comparable. |
| Frame JPEGs | none kept separately | 8.8 MB per minute (that build kept dropped frames' JPEGs) |

Reading: per frame, the YOLOE step is about 1.1 to 1.2 times slower on the Infinix. Per minute of video
the Infinix took about 1.3 to 2.4 times the Pixel's 1.4 min. The clips differ in length (75 s against 3.8
to 8 min), content and app build, so the safe statement is: same order of magnitude, the Infinix is
slower. Nothing finer is supported by these numbers.

## Not done yet

- **Same-clip comparison with the Pixel (card step 6):** kept frames, captions and search answers on the
  same two PXL clips. It needs the two PXL clips run on the Pixel (not available to the tester; the lead
  owns that phone). The Pixel cost reference above stands in for it and says what it can and cannot show.
- Confirmation of the matching counts above by the tester (they are an assistant's reading of the
  screenshots).
- Temperature and PSS during clip 1 and the second half of clip 2 (not sampled, cannot be recovered).

## Evidence files (`docs/results/second-phone/`)

| File | What it is |
|---|---|
| `infinix-2026-11-05-pipeline-console.txt` | The `EykonVideo` lines for all three runs, **copied by hand from the live console. Not a raw dump.** The `logcat -d -s EykonVideo` files saved afterwards came out empty (0 bytes), so this is the only record. |
| `infinix-2026-11-05-clip2-readings.txt` | Raw output of the PowerShell loop (battery level, temperature, PSS every 15 s, 10:22:42 to 10:25:02), re-encoded from UTF-16 to UTF-8 only. |
| `infinix-2026-11-05-meminfo-between-clips.txt` | `dumpsys meminfo com.eykon.memory` taken after clip 1 and before clip 2 (TOTAL PSS 795,987 kB), re-encoded to UTF-8. |
| `infinix-2026-11-05-battery-between-clips.txt` | `dumpsys battery` from the same moment (level 98, 33.7 C), re-encoded to UTF-8. |
| `infinix-2026-11-05-proc-status.txt` | `grep Vm /proc/28196/status` after all runs, copied by hand from the console. |
| `screenshots/infinix-2026-11-05-search-pens-01..09.jpg` | Phone screenshots (`adb shell screencap`, shrunk to 720 px wide JPEG; full-size PNGs kept by the tester) scrolling through the pens results, top to the "Saved videos (3)" list. |
| `screenshots/infinix-2026-11-05-search-keys-01..11.jpg` | The same for the repeated keys search (the 227 ms run). The first, cold keys run (2,193 ms) was not screenshotted. |

The screenshots show frames from our own PXL clips and the phone's notification bar. No Ego4D material.
