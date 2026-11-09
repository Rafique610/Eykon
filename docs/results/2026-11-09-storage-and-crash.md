# Storage per hour of video, and killing the app mid-stage (EYKO-116 parts 2 and 3)

**Part 3 (kill mid-stage) is DONE; part 2 (storage) has not been run yet.** Run by Zara Tahir on her Infinix X670. Answers supervisor questions C2 ("what does an hour
of video cost in storage?") and C3 ("what if the app is killed mid-write?"). Before this card there was one storage point: about 7 MB of
database for 27.8 min on the Pixel (`docs/results/2026-10-20-ego4d-baseline.md`).

## Setup

| Item | Value |
|---|---|
| Phone | Infinix X670, Android 13 |
| Build | `feature/video-memory` at `43d610e`, installed with `adb install -r` (never `connectedDebugAndroidTest`) |
| Source of the video | A 7 h 30 min screen recording of a work session (1920x1080, 60 fps, H.264 + AAC, 1.25 Mbps), no faces and no security concern (confirmed by Zara). Cut without re-encoding into pieces of 5, 10, 15 and 30 min (part 2) and nine of about 3 min (part 3). **Not camera video**: a screen recording is low-bitrate (about 0.12 MB per second against about 2.4 for the phone's own clips), so video copies per minute will be far smaller than for real phone video, and a still screen keeps few frames. Do not quote the numbers as the cost of an hour of camera video. |
| Free storage before | _ GB (`df -h /data`) |

## Part 2: storage by minutes of video

Taken with `python -I scripts/eyko116_storage.py --minutes <total so far> --label "<step>" --csv docs/results/vectors/storage/infinix-<date>-storage.csv`
(database and vector files in bytes, folders in KB; only sizes are read). Before any video: the app's data size in Settings and the
`memories.db` size are recorded first.

| Video added in total (min) | Database | Vector files (`*.vec`, `*.ids`) | Video copies | Frame files | Total app data | MB per minute of video |
|---|---|---|---|---|---|---|
| 0 (before) | _ | _ | _ | _ | _ | n/a |
| ~5 | _ | _ | _ | _ | _ | _ |
| ~15 | _ | _ | _ | _ | _ | _ |
| ~30 | _ | _ | _ | _ | _ | _ |
| ~60 | _ | _ | _ | _ | _ | _ |

**Reading:** _MB per minute for each part, which part grows fastest, what an hour costs; and what the video copies are (the app keeps a full copy of the clip)._

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

- **Part 2 (storage by minutes of video) is not run yet**; its table above is empty.
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

`docs/results/vectors/storage/` (part 2, not yet), `docs/results/vectors/crash/` (the nine raw kill logs `infinix-2026-11-10-kill-<stage>-run<n>.txt`, the link-check CSV and the uninterrupted-clip log); a screenshot is on the EYKO-116 card.
