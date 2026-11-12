# Storage per hour of video, and killing the app mid-stage (EYKO-116 parts 2 and 3)

**Parts 2 (storage) and 3 (kill mid-stage) are both DONE** (Part 3 on 10 Nov; Part 2 on 10 Nov, calculated for camera video and measured on a movie on 11 to 12 Nov). Run by Zara Tahir on her Infinix X670. Answers supervisor questions C2 ("what does an hour
of video cost in storage?") and C3 ("what if the app is killed mid-write?"). Before this card there was one storage point: about 7 MB of
database for 27.8 min on the Pixel (`docs/results/2026-10-20-ego4d-baseline.md`).

## Setup

| Item | Value |
|---|---|
| Phone | Infinix X670, Android 13 |
| Build | `feature/video-memory` at `43d610e`, installed with `adb install -r` (never `connectedDebugAndroidTest`) |
| Source of the video | A 7 h 30 min screen recording of a work session (1920x1080, 60 fps, H.264 + AAC, 1.25 Mbps), no faces and no security concern (confirmed by Zara). Cut without re-encoding into pieces of 5, 10, 15 and 30 min (part 2) and nine of about 3 min (part 3). **Not camera video**: a screen recording is low-bitrate (about 0.12 MB per second against about 2.4 for the phone's own clips), so video copies per minute will be far smaller than for real phone video, and a still screen keeps few frames. Do not quote the numbers as the cost of an hour of camera video. |
| Free storage before | 54 GB of 110 GB (`df -h /data`), 20:48 on 10 Nov; battery 83 %, plugged in, 31 C |

## Part 2: storage by minutes of video (done, 10 Nov 2026, 20:48 to 21:46)

The app was reset to 0 videos (database 135 KB; the app's data folder held 50 MB of leftovers from earlier test cards, so every growth figure below is
measured against that baseline). Four clips were added one after another and processed as one queue (about 58 minutes of processing for 60 minutes of video):
5, 10, 15 and 30 min (`p2-a` to `p2-d`, cut without re-encoding from the screen recording). `scripts/eyko116_storage_watch.py` took a reading each time a video
reached `ready`, with the running total of minutes finished (from the audio length in the log). Raw: `docs/results/vectors/storage/infinix-2026-11-10-storage.csv`
and the log `...-eykonvideo-watch.txt`. Database and vector files in bytes, folders in KB (`du -sk`, 1 KB = 1024 bytes).

**What the app keeps:** the full copy of each clip (made the moment the clip is added, **not** when it is processed), the 16 kHz audio file
(`audio16k.wav`, kept after processing), the database (all frames' rows, the kept frames' vectors, captions, sightings), `clip_vectors.bin`, and the frames
that survived the filters (the others are deleted at `finish`).

### Readings (growth against the baseline)

| Video finished in total (min) | Database | Database growth | Vector files (`*.vec`, `*.ids`) | Frame files | Total app data | App data growth | Growth per minute of video |
|---|---|---|---|---|---|---|---|
| 0 (baseline) | 135,168 B | n/a | 0 | 0 | 50,293 KB | n/a | n/a |
| 5.0 | 706,944 B | +558 KB | 0 | 248 KB | 721,366 KB | +671,073 KB | 131 MiB (all four copies are already in) |
| 15.0 | 1,096,208 B | +939 KB | 0 | 952 KB | 741,262 KB | +690,969 KB | 45 MiB |
| 30.0 | 1,703,936 B | +1,532 KB | 0 | 816 KB | 769,790 KB | +719,497 KB | 23 MiB |
| 60.1 | 2,727,936 B | +2,532 KB | 0 | 936 KB | 827,331 KB | +777,038 KB | **12.6 MiB** |

**Read the last column with care.** The four copies (676 MB) were all in the folder from the first reading, because the app copies a clip when it is added. So the per-minute
figure falls only because the minutes finished catch up with the copies already stored. The per-minute figure to use is the one at 60.1 minutes, when every clip is processed:
**about 12.6 MiB per minute of this video, 757 MiB (0.74 GiB) per hour.**

### Where the bytes are (60.1 minutes in total)

| Part | Size | Per minute of video | Per hour of video | Share of the growth |
|---|---|---|---|---|
| Full video copies (4 files) | 675.8 MB (660,656 KB) | 11.2 MB (7.3 to 8.1 MB for three clips, 14.7 for the 30-min one) | 675 MB | 85 % |
| 16 kHz audio files (`audio16k.wav`, kept) | 115.4 MB | 1.92 MB (exactly 16,000 Hz x 2 bytes) | 115 MB | 14.5 % |
| Database (rows, vectors, text index) | +2,532 KB | 42 KB | 2.5 MB | 0.3 % |
| Frame files kept | 936 KB | 16 KB | 0.9 MB | 0.1 % |
| `clip_vectors.bin` | 43 KB | 0.7 KB | 0.04 MB | under 0.01 % |

(Shares are of the total growth, 777,038 KB = 795.7 MB = 758.8 MiB. Sizes of files are in decimal MB; folder sizes from `du` are in 1024-byte KB, so the total growth is quoted in MiB: 12.6 MiB per minute, 757 MiB per hour.) Per clip:
`p2-a` 37.1 MB (7.4 MB/min), `p2-b` 73.4 MB (7.3), `p2-c` 122.1 MB (8.1), `p2-d` 443.2 MB (14.7); audio files 9.6, 19.2, 28.8 and 57.7 MB.

**What is in the database:** 4 videos, **10,820 frame rows but only 21 kept frames** (21 rows each in `image_vec` and `text_vec`, 21 texts, 48 sightings, 0 audio
windows because the screen recording has no speech). The `frames` table (1.35 MB) and its index (0.53 MB) are about 70 % of the database: the rows of dropped frames
stay, only their picture files are deleted.

**Reading:** an hour of this video costs about **0.75 GiB**, and **the copy of the video is almost all of it** (0.66 GiB), then the audio (0.11 GiB). The database,
the vectors and the frame pictures together are under 1 % (about 3.5 MB per hour). The number does not shrink if the video is processed more cleverly: the app keeps the
original file. Only deleting the copy after processing would change it (a product decision, not tested).

**Do not quote these numbers as the cost of an hour of camera video** (the source is a screen recording; for an hour of camera video, about 9.2 GB calculated, see Part 2 (b) below). A still screen keeps almost no frames (21 of 10,820), so the
database and vector growth are far below what moving camera video would give (the 5 Nov camera clips kept 10 and 16 of 224 frames in 75 s).

## Part 2 (b): one hour of camera video, calculated (11 Nov, on request of Rafique's review of PR #12)

`python scripts/eyko116_cost_per_hour.py` (laptop only, no phone). Formula: cost per hour = (video bitrate x 3600 s) + 115 MB audio +
(kept frames per hour x bytes per kept frame) + one 100-byte `frames` row for every sampled frame (3 per second).

| Input | Value | Source |
|---|---|---|
| Camera clips | 1080p HEVC, **20.03 Mbps** (2.50 MB/s) | ffprobe of the two PXL clips |
| Kept frames | 10 per 74.5 s and 16 per 75 s = **483 to 768 per hour** | Part 3 runs, same as 5 Nov |
| Bytes per kept frame | picture 44.6 KB + `.vec` 3.6 KB (512 + 384 float32) + text 0.4 KB + sightings (5.3 to 8.4 per kept frame at 2.07 KB) = **about 60 to 66 KB** | `db-after-part2` (21 kept frames, 48 sightings) |
| Frame rows | 100 B x 3 per second = 1.1 MB per hour | same database, 10,820 rows |

| Clip | Copy | Audio | Kept frames | Frame rows | **Total per hour** |
|---|---|---|---|---|---|
| Camera clip 1 | 9.01 GB | 115 MB | 29 MB | 1.1 MB | **9.16 GB** |
| Camera clip 2 | 9.01 GB | 115 MB | 51 MB | 1.1 MB | **9.18 GB** |
| Screen recording (check) | 0.67 GB | 115 MB | 1.1 MB | 1.1 MB | 0.79 GB (**measured 757 MiB = 0.79 GB**) |

**Reading:** an hour of this phone's camera video costs about **9.2 GB, calculated, not measured**; the copy of the video is 98 % of it.
The same formula run on the Part 2 screen recording gives 0.79 GB against 0.79 GB measured, so the formula holds where it can be checked.
**Copy equals source (checked on four files, plus Rafique's camera clip on the Pixel):**
- Part 2, screen clips: the four source clips add up to 675,833,518 bytes and the copies measured 675.8 MB.
- 11 Nov, movie pieces (the test movie, cut with `-c copy` to 5, 10, 15 and 25 min): the app's copies in `files/videos/<id>/` were byte for byte the same size as the sources, 78,208,453, 176,247,364, 342,238,760 and 462,150,353 (`ls -l` through `run-as`).
- Camera clip: not checked on the Infinix. Rafique's Pixel run (EYKO-119) logged a copy of 186,496,604 bytes for a 186,496,604-byte source (kit clip `PXL_20261014_094359202`, 186,496,580 bytes, plus 24 test bytes). The copy is a straight copy at add time, so the rule does not depend on the bitrate.

**Part 2 (a), measured on a movie (11 to 12 Nov): done.** The test movie (a feature film, a local file, not in the repo; 1920x804 H.264 at 2.25 Mbps, 5.1 audio) was cut
with `-c copy` into four non-overlapping pieces of 5, 10, 15 and 25 min (a 30 min piece would be 594 MB, over the app's 500 MB limit): 1,058,844,930 bytes over 3,300 s, 2.57 Mbps.
The app's data folder grew from 50,296 KB (baseline, 0 videos) to 1,231,422 KB (all four ready), by **1,181,126 KB = 1,209.5 MB for 55 min = 1.32 GB per hour**.
Raw: `docs/results/vectors/storage/infinix-2026-11-11-storage-movie.csv` and the logs beside it.

| Part | Measured (55 min) | Formula (55 min) |
|---|---|---|
| Copies of the video | 1,058.8 MB (each copy exactly its source's size; `du` shows 1,035,060 KB) | 1,058.8 MB |
| 16 kHz audio and other files in the video folders | 107.5 MB (audio is 105.6 MB) | 105.6 MB |
| Kept frame pictures | 27.5 MB (831 kept of 9,904 frames, 33 KB each) | |
| Database growth | +14.6 MB (831 kept frames, 1,604 sightings, 17.5 KB per kept frame) | |
| Kept frames and frame rows together | 42.1 MB | 45.6 MB (picture 44.6 KB from the screen frames, 53 KB per kept frame) |
| Search copy (`*.vec`) | 0 (no search was run) | |
| **Total per hour** | **1.32 GB** | **1.32 GB (+0.1 %)** |

**Reading:** the formula predicts both measured runs: the screen recording (0.79 GB per hour, calculated 0.79) and the movie (1.32 GB, calculated 1.32, +0.1 %). The copy and the audio match
to the byte; the kept-frame term is about 8 % high (picture 44.6 KB from the screen frames against 33 KB here), and the total hides that small error. The movie kept 906 frames per hour
(camera clips: 483 to 768), so it was a harder case for that term than the camera clips. The 9.2 GB per camera hour is still **calculated**: no hour of camera video was run.

**How the run went (for honesty):** the 5 min video finished at 21:12. The USB cable dropped twice, so the watcher stopped and only two readings exist (after video 1 and at the end). At 23:20,
right after `link` of the 25 min video, Android killed the app's process in the background ("excessive cpu ... limit=2", `ActivityManager`, line in
`docs/results/vectors/storage/infinix-2026-11-12-eykonvideo-movie-logcat.txt`). When the app was opened again at 00:00 the job resumed from its saved stage and finished at 00:13
(`latest` took 740 s for 910 sightings). The storage numbers are not affected; this is another background kill of the pipeline, the case EYKO-44 addresses.

**Limits:** the picture size (44.6 KB) comes from screen frames (33 KB on the movie); camera frames may be larger, but at 480 to 770 kept frames per hour even
3 times larger changes the total by under 0.1 GB. Kept frames per hour comes from two 75-second clips. No hour of video was run: the 9.2 GB figure is **calculated**, from the measured bitrate (ffprobe) and the measured sizes per kept frame, and the same formula reproduces two measured runs (screen recording 0.79 GB, movie 1.32 GB).

## Part 3: kill the app in the middle of a stage (done, 10 Nov 2026, 01:29 to 02:08)

3 stages, 3 runs each (9 runs). The kill is `adb shell am force-stop com.eykon.memory`, a fixed delay after the end of the stage before, taken
with `scripts/eyko116_kill.py`. Right after the kill the script reads the job row from the database (the stage it saved), then reopens the
app (`monkey` launcher intent) and watches `logcat -s EykonVideo` until `finish ... ready`. After each run `scripts/eyko116_link_check.py` pulls the database and
runs the ten counts from `VideoLink.kt` (every count must be 0). The app was reset to 0 videos before every run.

**Clips used:** the two real camera clips `PXL_20261014_094359202.mp4` (74.5 s, 10 kept frames) and `PXL_20261014_094903187.mp4` (75 s, 16 kept
frames), alternating. The 3-minute screen-recording clips cannot be used for this: a still screen keeps 1 frame, so `scene` ran 2.5 s, `small_objects`
0.1 s and `embed_texts` 0.8 s (`docs/results/vectors/crash/infinix-2026-11-10-uninterrupted-clip1-eykonvideo.txt`), too short to kill inside.

| Run | Clip | Stage killed in | Delay after previous stage | Saved stage at the kill | Job resumed at the same stage? | Video reached ready? | Link check (all 0?) |
|---|---|---|---|---|---|---|---|
| 1 | …094359 (74.5 s) | scene | 5 s | dedup | yes (new pid 24032, `scene` redone 16.1 s) | yes, 01:30:55 | yes |
| 2 | …094903 (75 s) | scene | 2 s | dedup | yes (pid 25624, `scene` 25.0 s) | yes, 01:37:18 | yes |
| 3 | …094359 | scene | 10 s | dedup | yes (pid 27562, `scene` 16.3 s) | yes, 01:41:02 | yes |
| 4 | …094903 | small_objects | 5 s | scene | yes (pid 28540, `small_objects` 45.3 s) | yes, 01:46:34 | yes |
| 5 | …094359 | small_objects | 15 s | scene | yes (pid 29519, 32.1 s) | yes, 01:51:03 | yes |
| 6 | …094903 | small_objects | 25 s | scene | yes (pid 30316, 46.5 s) | yes, 01:56:58 | yes |
| 7 | …094359 | embed_texts | 0.1 s | embed_images | yes (pid 31166, `embed_texts` 1.6 s) | yes, 02:00:10 | yes |
| 8 | …094903 | embed_texts | 0.25 s | embed_images | yes (pid 32471, 1.7 s) | yes, 02:05:12 | yes |
| 9 | …094359 | embed_texts | 0.4 s | embed_images | yes (pid 2344, `embed_texts` logged at 02:07:48) | yes, 02:08:35 | yes |

**Reading:** all 9 runs were killed with the video still `processing`, all 9 resumed in a new process at the stage after the saved one, all 9 reached
`ready`, and every one of the ten link counts was 0 after every run (`docs/results/vectors/crash/infinix-2026-11-10-link-check.csv`). The numbers after the
restart match the uninterrupted runs of 5 Nov: clip …094359 gives 10 kept frames, 6 objects found and 53 sightings (runs 1, 3, 5, 7, 9); clip …094903 gives 16
frames, 4 found and 134 sightings (runs 2, 4, 6, 8). The job row saved the last finished stage (`dedup`, `scene` or `embed_images`) every time, which is
the stage the job resumed after. Only the interrupted stage was done twice, so the kill cost the time of that one stage.

## Not tested / limits

- **Part 2 limits:** one video source (a screen recording, 1.25 Mbps), one phone; **no search was run in this part, so the memory-mapped search copy (`*.vec`, `*.ids`)
  was never built and shows 0.** From the row counts it would be tiny here (21 vectors per table, 43 KB for the 512-number images); a library with many more
  kept frames is what EYKO-109 and the Part 1 sweep measure. Settings (Apps, Eykon, Storage) after the test:
  App size 162 MB, **User data 847 MB**, Cache 111 kB, Total 1.01 GB. The 847 MB agrees with the measured 827,331 KB (827,331 x 1024 = 847.2 million bytes). A first Settings
  screenshot taken at 22:19 still showed the figures from before the test (User data 51.74 MB): Settings keeps a cached figure, so use the reading after it refreshes. Screenshot on the card.
- **Part 3 used `am force-stop`**, a clean kill by the system. A kill by the phone's power manager or by memory pressure (signal 9 from `system_server`,
  see `2026-11-09-background-kill-mapped-native.md`) was not tried here. I expect the same resume, because the job row does not depend on how the process ends, but I did not measure it.
- **Where inside a stage the kill landed is known only to the stage**, not to the frame. `embed_texts` lasts about 0.4 to 1.7 s, so the kill is inside it
  only because the saved stage was still `embed_images` and no `embed_texts` line came from the old process. The three `embed_texts` delays (0.1, 0.25, 0.4 s) therefore
  show the same thing three times; the other two stages had windows of 16 to 49 s.
- **Two clips only (74.5 s and 75 s)**, each used 4 or 5 times, with the app reset to 0 videos before every run. A longer video, a full database, or a second
  video queued behind the first was not tested. A kill during `split`, `filter` or `latest` was not tested (the card names three stages).
- **Search after the restart** was not run; the link check and the matching counts (frames, objects, sightings) are the evidence that the data is whole.
- **Infinix only**; the A32 was not used.
- **A failed first attempt is kept for honesty:** the first four tries of run 1 failed at `dedup` with "the image model is missing", because the app could not read
  the folder the models were pushed into (it was owned by the `shell` user and closed to the app). Fixed with `chmod 777` on that folder; no model changed. The
  3-minute screen-recording clips were also dropped for this part (see above).

## Evidence files

`docs/results/vectors/storage/` (part 2: the readings CSV and the watch log), `docs/results/vectors/crash/` (the nine raw kill logs `infinix-2026-11-10-kill-<stage>-run<n>.txt`, the link-check CSV and the uninterrupted-clip log); a screenshot is on the EYKO-116 card.
