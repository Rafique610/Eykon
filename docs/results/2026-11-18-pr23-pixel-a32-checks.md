# PR #23 on the phones: mediaProcessing, the 6 h limit, the maker card, A32 bitrate; A32 in the background (EYKO-172, EYKO-168, 18 Nov 2026)

**Build.** `feature/video-memory` at 3992a35 (PR #23 squash-merged; the phones ran its branch head 7df5097, the same app code), both APKs
with `adb install -r` (never `connectedDebugAndroidTest`).
**Phones** (rule "Which phone a card runs on"): Pixel 9 Pro XL (Android 17) for everything that needs Android 15+; Samsung A32 (SM-A325F,
Android 13, One UI 5.1) only for the Samsung card, a Samsung bitrate and Samsung background behaviour.
**Data.** Whole app data backed up first on both phones (Pixel `D:\eykon-cache\backups\pixel-types-2026-11-17`, A32
`D:\eykon-cache\backups\a32-eyko168-2026-11-18`). Afterwards only the test videos' folders were deleted, by their `read` ids, and the
databases put back (same SHA-256; folder lists match the backups).
**Clips.** Kit clips with a trailing `free` atom (byte-different, same frames), added through the app's Video tab and the system file
picker, driven over adb.

| # | Card | Phone | What was done | Expected | Seen | Evidence |
|---|---|---|---|---|---|---|
| 1 | 172 | laptop + Pixel | `testDebugUnitTest`; `am instrument` VideoLatestTest, VideoCaptureTest, VideoRerunSafetyTest, VideoSplitTest | all pass | **JVM 125 of 125**; on-device **OK (26 tests)**; app database unchanged | `head3/pr23/pixel-ondevice-tests.txt` |
| 2 | 172 | Pixel | kit clip 2, Home | service type mediaProcessing; ready in the background | `types=0x00002000` (**mediaProcessing**; dataSync is 0x1); ready 2 min 32 s after adding, 16 kept, 134 sightings | `head3/pr23/pixel-service-type.txt` |
| 3 | 172 | Pixel | `device_config put activity_manager media_processing_fgs_timeout_duration 120000`, kit clip 2, Home, screen off | stop with the timeout reason, "paused" note, no crash | 3 min 19 s in: `worker stopped, reason foreground service timeout (Android 15+ 6 h a day limit) (code -128)`; **"Video processing paused" note shown**; **no** "did not stop within its timeout" or crash anywhere in the logcat. WorkManager retried; Android refused the service from the background (`ForegroundServiceStartNotAllowedException`), so the last stage (`finish`) ran as plain work: **ready** 15 s later | `head3/pr23/pixel-timeout-log.txt` |
| 3b | 172 | Pixel | open Eykon after the limit (owner, 18 Nov 16:01, same 2-min limit) | note cleared | **Not cleared (bug)**: the job was ready at 16:00:58, the owner opened Eykon from its icon and the note stayed while he was in the app. Cause: only a new foreground start cleared it, and with the queue empty none happens. **Fixed** in `VideoJobWorker`: the note is cleared when the worker finds the queue empty (this is what opening the app runs) and when a run ends with nothing queued. Re-run with the fix (16:07-16:11): note shown at the stop, **gone once the video was ready**. JVM 125 of 125 | `head3/pr23/pixel-paused-note-log.txt`, `pixel-paused-note-after-open.png`, `pixel-paused-note-fixed-log.txt` |
| 3c | 172 | Pixel | `device_config delete …` | default limit back | done (`get` returns null) | — |
| 4 | 172 | Pixel | Video tab | no maker card (Google) | no card | `head3/pr23/pixel-no-maker-card.png` |
| 5 | 172 | A32 | Video tab | Samsung card | **shown**, with "Open Eykon's settings" | `head3/pr23/a32-samsung-card.png` |
| 5b | 172 | A32 | owner set Battery to Unrestricted; Eykon opened afresh | card gone | **card gone** (Eykon on the battery allow-list, `deviceidle whitelist: user`). Not checked: whether it goes on returning from Settings without a redraw | `head3/pr23/a32-no-card-unrestricted.png` |
| 6 | 172 | A32 | Samsung bitrate | fill the empty row | **1080p (the default): 17.3 Mbps**, median of 85 camera files in the phone's media index (size ÷ duration; range 16.2-30.0), so about 130 MB a minute and 500 MB = 3.9 min. No video recorded or copied (privacy); codec not read; no 4K file on the phone | `content query` on `DCIM/Camera` |
| 7 | 168, step 1 | A32 | kit clip 2, Home, screen off | ready without opening the app | **ready** 5 min 56 s after adding; no stop or kill line | `head3/pr23/a32-background-log.txt` |
| 8 | 168, step 2 | A32 (Unrestricted) | two clips queued, Home, `adb reboot` right after the first clip's `filter`; owner unlocked, did **not** open Eykon | resumes by itself | **yes**: Eykon started from the boot broadcast about 2.5 min after the phone was back, resumed at `dedup` (the stage after the saved one), both videos ready (16:34, 16:37) without the app being opened | `head3/pr23/a32-168-steps-2-4-log.txt` |
| 9 | 168, step 3 | A32 (Unrestricted + Sleeping apps) | owner added Eykon to Sleeping apps; clip, Home, reboot after `filter`; not opened | — | **resumed by itself**: `Start proc … for broadcast … BOOT_COMPLETED`, "Background started FGS: Allowed", resumed at `dedup`, ready 17:04:49 | same |
| 10 | 168, step 4 | A32 (Unrestricted + Deep sleeping) | clip, Home, owner added Eykon to Deep sleeping apps mid-job | — | **inconclusive**: the job reached ready (17:11:19) about when the setting was added. A new clip with Deep sleeping already on ran in the background to ready in 3.3 min | same |
| 11 | 168, extra | A32 (**Optimized** + Deep sleeping) | owner set Battery back to Optimized; new clip from the app, Home | — | **ready in 3.3 min** in the background. Standby bucket 10 (active), because adding the clip opens the app | same |

## Reading

- **mediaProcessing works on Android 17**, and the 6 h limit behaves as PR #23 planned: a clean stop, the paused note, no crash.
- Once the limit is hit, Android refuses a new foreground service from the background, so WorkManager carries on **as plain work**.
  Here only `finish` was left, so the video still became ready. A long queue would carry on more slowly, under the standby-bucket rules
  (research doc, Part 1).
- **The paused note outlived the pause** (step 3b) and is now fixed: it clears when the queue is empty.
- **The A32 holds a background job** with the screen off, on One UI 5.1, with Eykon in standby bucket 40 ("rare") at the start.
- **After a restart the A32 resumes the job by itself** (unlike the Infinix, EYKO-170), also with Eykon in Sleeping apps.
- **Samsung's sleep lists did not stop a job the person just started**, with battery Unrestricted or Optimized. What one UI does to an
  app left unopened for days (the 3-day rule) is not shown: adding a clip always makes the app active, and a natural 3-day wait was
  dropped from the card. Answer for D1 on the A32: the background job holds; the Samsung card's advice is a safeguard, not a fix
  for something seen here.
- The Samsung bitrate row in `docs/research/2026-11-16-head3-background-and-limits.md` is filled: 500 MB was about 4 minutes on the A32 too.

## Owed (owner, phone in hand)

1. ~~Pixel: open Eykon after a limit stop and check that the paused note goes (step 3b).~~ Done 18 Nov: it did not; fixed and re-checked.
2. ~~A32: Battery to Unrestricted~~ done 18 Nov: card gone; Battery set back to Optimized by the owner.
3. ~~A32: EYKO-168 steps 2-4~~ done 18 Nov with the owner (rows 8 to 11). Owner removes Eykon from Sleeping and Deep sleeping apps.
A32 clean-up: the six test folders removed by id, database restored (same SHA-256), folder list matches the backup, test clips removed.
