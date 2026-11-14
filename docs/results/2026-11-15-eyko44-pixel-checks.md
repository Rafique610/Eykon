# EYKO-44 on the Pixel: background, reboot and the review fixes (15 Nov 2026)

Run by Rafique (reviewer) to finish the review of PR #18. Zara's Infinix checks are in `2026-11-12-eyko44-workmanager-phone-checks.md`.

| Item | Value |
|---|---|
| Phone | Pixel 9 Pro XL, Android 17 (SDK 37), USB |
| Build | `zara/eyko-44-workmanager` at ef8afcf: her work merged with `feature/video-memory` f046ecb (EYKO-126 read in place, EYKO-127 file picker) plus the two review fixes (worker returns at once when no job is waiting; the file name in the notification) |
| Data | app data backed up first (`D:\eykon-cache\backups\eyko44-2026-11-15`) and restored at the end, with the regular build reinstalled |

## Results

| Check | What was done | Result |
|---|---|---|
| On-device tests | `VideoJobSchedulingTest`, `VideoWorkerTest`, `VideoCaptureTest`, `VideoRerunSafetyTest`, `VideoFinishTest`, `VideoLinkTest` | **37/37 pass** (`eyko44-pixel/pixel-ondevice-tests.txt`) |
| Background | kit clip `eyko44_bg.mp4` (74.5 s) added, then Home; the app was not opened again | `isForeground=true`, notification **"Video 1 of 1, eyko44_bg.mp4: split"**; ready 115 s after adding (10 kept, 6 found, 54 sightings, as on 11 Nov); the service ended by itself |
| Queue + reboot mid-job | `eyko44_long.mp4` (4 min 58 s, 743 MB) and `eyko44_bg2.mp4` (75 s) added back to back, Home; notification "Video 1 of 2, eyko44_long.mp4: split"; **phone restarted at 01:06:22, after the long clip's `filter`** | booted 01:07:07; unlocked 01:07:14; **Eykon's process started by itself at 01:08:01 with the home screen in front** (the app was never opened); notification "Video 1 of 2, eyko44_long.mp4: **dedup**": it resumed at the stage after the saved one. Both videos then reached ready (long 20:14:49 UTC, short 20:23:57 UTC): jobs `done`, 0 attempts, no error; kept frames 13 and 16, as in earlier runs |
| Empty runs (review fix) | two adds in a row, so one extra run was appended | **no "foreground service not allowed" line** in the log after the queue finished (Zara's check 4 had three) |

## What this says about the Infinix reboot result

On the Infinix (check D) the work stayed saved but did not start until the app was opened. On the Pixel the same code started by
itself 47 s after the first unlock. So the code and WorkManager's boot handling work on stock Android; the Infinix holds it back.
The likely cause is the phone maker's own auto-start control (Transsion phones block apps from starting after a reboot unless the
person allows it), **not proven**: it needs Zara's phone (allow auto-start for Eykon, reboot mid-job again).

Note: Android does not let any app run after a restart until the phone is unlocked once (the app's data is encrypted until then).

## Seen on the way

- `latest` in the background after the reboot took 201 s for 134 sightings (about 1.5 s each); with the app in front on 11 Nov it was
  about 0.25 s each. Background work gets less CPU. Not measured further here (Head 3 time per stage is EYKO-117 / EYKO-120).
- Android 15+ `dataSync` daily limit (about 6 h): the foreground service starts and runs on Android 17; the limit itself was not reached.

## Evidence

`eyko44-pixel/`: on-device test output; the app's log lines before the reboot and the tail after it (the log buffer had rolled over,
so the long clip's later lines are not in it; the job rows in the database are the record: `done`, 0 attempts, no error).
