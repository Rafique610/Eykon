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
| 3b | 172 | Pixel | open Eykon after the limit | note cleared | **not checked**: the Pixel had locked itself and cannot be unlocked over adb. Seen: the note was still up after the video was ready, because only a new foreground start clears it | — |
| 3c | 172 | Pixel | `device_config delete …` | default limit back | done (`get` returns null) | — |
| 4 | 172 | Pixel | Video tab | no maker card (Google) | no card | `head3/pr23/pixel-no-maker-card.png` |
| 5 | 172 | A32 | Video tab | Samsung card | **shown**, with "Open Eykon's settings" | `head3/pr23/a32-samsung-card.png` |
| 5b | 172 | A32 | Battery to Unrestricted, come back | card gone | **not done**: a Settings change on the owner's phone, left for the owner. Review note: the card is worked out when the screen is drawn and nothing redraws it on return, so it may stay until the next redraw | — |
| 6 | 172 | A32 | Samsung bitrate | fill the empty row | **1080p (the default): 17.3 Mbps**, median of 85 camera files in the phone's media index (size ÷ duration; range 16.2-30.0), so about 130 MB a minute and 500 MB = 3.9 min. No video recorded or copied (privacy); codec not read; no 4K file on the phone | `content query` on `DCIM/Camera` |
| 7 | 168, step 1 | A32 | kit clip 2, Home, screen off | ready without opening the app | **ready** 5 min 56 s after adding; no stop or kill line | `head3/pr23/a32-background-log.txt` |
| 8 | 168, steps 2-4 | A32 | restart mid-job; Sleeping apps by hand; Sleeping apps mid-job | — | **not done**: each needs the owner (unlock after a restart; Settings changes). Clips `bg_s2_*`, `bg_s3_*`, `bg_s4_c2` are in the A32's Movies folder for it | — |

## Reading

- **mediaProcessing works on Android 17**, and the 6 h limit behaves as PR #23 planned: a clean stop, the paused note, no crash.
- Once the limit is hit, Android refuses a new foreground service from the background, so WorkManager carries on **as plain work**.
  Here only `finish` was left, so the video still became ready. A long queue would carry on more slowly, under the standby-bucket rules
  (research doc, Part 1).
- **Small fix suggested:** clear the paused note when the queue finishes (today it stays until the next foreground start).
- **The A32 holds a background job** with the screen off, on One UI 5.1, with Eykon in standby bucket 40 ("rare") at the start.
- The Samsung bitrate row in `docs/research/2026-11-16-head3-background-and-limits.md` is filled: 500 MB was about 4 minutes on the A32 too.

## Owed (owner, phone in hand)

1. Pixel: open Eykon after a limit stop and check that the paused note goes (step 3b).
2. A32: Battery to Unrestricted, back to Eykon: is the card gone? Then set it back (step 5b).
3. A32: EYKO-168 steps 2-4 (restart mid-job without opening the app; Sleeping apps by hand, then restart; Sleeping apps mid-job).
