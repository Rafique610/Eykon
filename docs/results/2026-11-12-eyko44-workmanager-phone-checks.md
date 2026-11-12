# EYKO-44: video jobs as WorkManager foreground work, Infinix checks (12 Nov 2026)

Phone: Infinix X670, Android 13 (SDK 33). Build: `zara/eyko-44-workmanager` at f006f09 plus the "Video n of m" notification text (added after these runs, text only).
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

## The "excessive cpu" kill

On 11 Nov, without WorkManager, Android killed the app in the background: `ActivityManager: Killing ... com.eykon.memory (adj 900): excessive cpu 1174680 during 300051 ... limit=2` after 26 min of work. The checks above are 5 minutes each and show no kill; Rafique's check 4 (the four movie pieces, 55 min, in the background) is the proper test and is **not yet run**.

## Not tested

- Android 15 `dataSync` time limit and the timeout callback (this phone is Android 13; the worker logs the stop reason by name if it happens). Whether `mediaProcessing` fits is for EYKO-122 (Taha), which has not started.
- Check 4: the four pieces (5, 10, 15, 25 min) queued and left in the background.
- The reboot path when Android refuses the foreground service from the background (the fallback to plain work was not exercised on the phone).

## Tests

119 JVM tests pass. On the phone: `VideoWorkerTest` and `VideoJobSchedulingTest`, 12 tests, OK (includes the new test for the "Video n of m" count).
