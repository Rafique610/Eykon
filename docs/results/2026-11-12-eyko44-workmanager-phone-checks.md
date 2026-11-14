# EYKO-44: video jobs as WorkManager foreground work, Infinix checks (12 Nov 2026)

Phone: Infinix X670, Android 13 (SDK 33). Checks A-D below were made on 12 Nov, check 4 on 14 Nov. Build: `zara/eyko-44-workmanager` at f006f09 plus the "Video n of m" notification text (added after these runs, text only).
Clip for every check: `p2m-a-05min.mp4` (5 min 0 s, 78,208,453 bytes, a 5-minute piece of the EYKO-116 movie). The app was reset to the empty baseline before each check. Battery setting for Eykon in Android: Optimized (the default).
Raw files: `docs/results/head3/eyko44/` (Eykon log lines, 30-second samples of process / foreground service / battery, link check CSV).

## Result

| Check | What was done | Reached ready | Time | Process | Foreground service | Link check |
|---|---|---|---|---|---|---|
| A | app in front | yes | 329 s (5.5 min) | one process | `isForeground=true` until ready | all counts 0 |
| B | Home, then 5 apps in front (social app and 2 websites from it, music player, mail, a job-site app) | yes | 404 s (6.7 min) | one process, never killed | `isForeground=true` until ready | all counts 0 |
| C | app swiped away from recents after about 1 minute | yes, without reopening the app | 326 s (5.4 min) | same pid before and after the swipe | `isForeground=true` until ready | all counts 0 |
| D | phone restarted mid-job (after the filter stage) | **only after the app was opened** | see below | new process after the reopen | started when the app opened | all counts 0 |

Time is from adding the video to "ready" in the app. The pipeline did the same work in all four: 901 frames split, 78 kept by the filter, 51 after dedup, 84 sightings.

## Check D: reboot, in detail

- The reboot came after the **filter** stage. The job record (not the log, which the restart wiped) said `status=running, stage=filter, attempts=0`.
- WorkManager kept the work saved as `ENQUEUED` (attempt 1). Nothing was lost.
- About 8 minutes after the boot there was still **no Eykon process**. The work did not start by itself. Eykon holds `RECEIVE_BOOT_COMPLETED` and WorkManager's boot receiver is registered, so I cannot say from the logs why it waited. Android's app settings showed nothing restricting it (battery: Optimized, notifications allowed). A phone-maker auto-start rule is a guess and is not shown by any setting I could see. **Cause not established.**
- When the app was opened (12:27:23) WorkManager moved the saved work item to the foreground (`WM-Processor: Moving WorkSpec ... to the foreground`, then `Started foreground service`). **The path that ran was the foreground service, not plain work.** The app was in front at that moment, so this does not show what happens if Android refuses the service from the background.
- The job continued at the **dedup** stage (the stage after filter). Split and filter did not run again. It reached ready at 12:31:13, 3.8 min after the reopen, with `attempts=0`.

## Background time vs in-front time

The card asks about the 21.2 vs 11 min gap (an 8-minute Ego4D clip, 20 Oct, in-app loop). Here, the same 5-minute clip took 5.5 min in front (A) and 6.7 min with 5 other apps in front (B): 1.2 min more. These are different clips and builds, so they do not prove the old gap is closed, but the stall that took the in-app loop to twice the time did not appear.

## Check 4: four movie pieces in the background (14 Nov 2026)

Pieces of the EYKO-116 movie: 5, 10, 15 and 25 min (78,208,453 / 176,247,364 / 342,238,760 / 462,150,353 bytes), 55 min of video in all. App reset to empty first. I added the four pieces one after another through the photo picker (about 1 min apart), then pressed Home. **The app was not opened again** until the run was over. The phone was on USB (so battery change is not battery use). Raw files: `docs/results/head3/eyko44/E-movie-4pieces-*` and `link-check.csv`.

| | |
|---|---|
| Reached ready | **all 4**, without reopening the app |
| First copy to last finish | 17:51:30 to 19:27:38 = **96 min** for 55 min of video (1.75 min of work per minute of video) |
| Added to ready, per piece | 5 min: 5.7 min; 10 min: 22.1 min; 15 min: 45.9 min; 25 min: 92.4 min (they ran one after another, so later ones waited) |
| Process | the **same process** (pid 16325) in all 190 samples; never killed |
| `excessive cpu` kill | **none** in the log |
| Foreground service | `isForeground=true` while a job ran |
| Link check | all counts 0 for all 4 videos; every job `done` at `finish`, 0 attempts, no error |
| Battery / heat | 56% to 47% (on USB), 27.5 to 39.4 C |

Only the first video started with the app in front (I was still adding the clips); the other three started and ran with the app in the background.

**Warning at the end:** at 19:27:39, just after the last video finished, the log shows three lines `foreground service not allowed here, running as plain work: ForegroundServiceStartNotAllowedException` (Android refused to start the foreground service from the background). So the fallback to plain work did run once. All four videos were already ready. I did not find out what started those three extra runs, so I do not know the cause.

The watcher's own `wall` figure (47.7 min) is only the 25-min piece, from its split to its finish; it is not the total.

## The "excessive cpu" kill

On 11 Nov, without WorkManager, Android killed the app in the background: `ActivityManager: Killing ... com.eykon.memory (adj 900): excessive cpu 1174680 during 300051 ... limit=2` after 26 min of work. In check 4 the same kind of work ran 96 min in the background with the foreground service and the process was not killed. This run does not say whether the foreground service is the reason, only that the kill did not happen.

## Not tested

- Android 15 `dataSync` time limit and the timeout callback. The app targets SDK 35, but this phone is Android 13, so the limit cannot happen on it. The worker logs the stop reason by name if it does. Whether `mediaProcessing` fits is for EYKO-122 (Taha), which has not started.
- Why the work did not start after a reboot until the app was opened (check D). Cause not established.
- Battery use per minute of video (the phone was on USB).
## Tests

119 JVM tests pass. On the phone: `VideoWorkerTest` and `VideoJobSchedulingTest`, 12 tests, OK (includes the new test for the "Video n of m" count).
