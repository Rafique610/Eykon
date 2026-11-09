# Storage per hour of video, and killing the app mid-stage (EYKO-116 parts 2 and 3)

**DRAFT: nothing here has been run yet.** Filled in by Zara Tahir on her Infinix X670. Answers supervisor questions C2 ("what does an hour
of video cost in storage?") and C3 ("what if the app is killed mid-write?"). Before this card there was one storage point: about 7 MB of
database for 27.8 min on the Pixel (`docs/results/2026-10-20-ego4d-baseline.md`).

## Setup

| Item | Value |
|---|---|
| Phone | Infinix X670, Android 13 |
| Build | `feature/video-memory` at `43d610e`, installed with `adb install -r` (never `connectedDebugAndroidTest`) |
| Source of the video | _what the clips are, where they came from, bitrate; say if it is a screen recording or camera video_ |
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

## Part 3: kill the app in the middle of a stage

3 stages, 3 runs each (9 runs). The kill is `adb shell am force-stop com.eykon.memory`, a fixed delay after the end of the stage before, taken
with `python -I scripts/eyko116_kill.py --stage <stage> --delay <s> --log docs/results/vectors/crash/infinix-<date>-kill-<stage>-run<n>.txt`.
After each run the database is pulled and checked with `python -I scripts/eyko116_link_check.py --label "<stage> run <n>" --csv docs/results/vectors/crash/infinix-<date>-link-check.csv`
(the ten counts from `VideoLink.kt`; every count must be 0).

| Run | Stage killed in | Delay | Job resumed at the same stage? | Video reached ready? | Link check (all 0?) | Notes |
|---|---|---|---|---|---|---|
| 1 | scene | _ | _ | _ | _ | |
| 2 | scene | _ | _ | _ | _ | |
| 3 | scene | _ | _ | _ | _ | |
| 4 | small_objects | _ | _ | _ | _ | |
| 5 | small_objects | _ | _ | _ | _ | |
| 6 | small_objects | _ | _ | _ | _ | |
| 7 | embed_texts | _ | _ | _ | _ | |
| 8 | embed_texts | _ | _ | _ | _ | |
| 9 | embed_texts | _ | _ | _ | _ | |

**Reading:** _did every job resume and reach ready; any run with a non-zero count, with the logcat lines that show the resume._

## Not tested / limits

- _Fill in after the runs._

## Evidence files

`docs/results/vectors/storage/`, `docs/results/vectors/crash/` (raw kill logs and the link-check CSV); storage and logcat screenshots are on the EYKO-116 card.
