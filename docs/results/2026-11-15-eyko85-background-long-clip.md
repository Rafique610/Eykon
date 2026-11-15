# EYKO-85: an 8-minute clip finishes with the app in the background (Pixel, 15 Nov 2026)

Acceptance check for EYKO-44 (WorkManager + foreground notification), gap G10. Before EYKO-44, an 8-minute Ego4D clip took 21.2 min instead of about 13, because jobs ran only while the app was in front (`2026-10-20-ego4d-baseline.md`).

**Phone.** Pixel 9 Pro XL, Android 17, **unplugged** (adb over Wi-Fi) so Doze could happen. **Build:** `feature/video-memory` at d93c56b, which includes the faster split.
**Clip.** `eyko85_8min.mp4`: kit clip 1 looped with `ffmpeg -stream_loop 6 -t 480 -c copy`. 480.0 s, 1,197,672,204 bytes, Pixel-recorded HEVC.
**How.** The clip was added through the system file picker, driven over adb, with the app checked to be in front before every tap. Then Home, then the screen was switched off (the phone locks). Every 30 s for 10 minutes the script read the Eykon log, the Doze state (`dumpsys deviceidle`), the battery and the app's notification text. Then the screen was woken and the logs were saved. The app's data was backed up first and restored after each run; the database is byte-identical to the backup.
**Files:** `eyko85/run1-normal/`, `eyko85/run2-battery-saver/` (`samples.csv`, Eykon log, system log lines, start and end readings), `eyko85/run2a-extreme-saver/suspended.png`.

## Results

| | Run 1: normal | Run 2: Battery Saver on | Extreme Battery Saver on |
|---|---|---|---|
| Did the job keep going with the app in the background and the screen off? | **yes** | **yes** | **no: Eykon is paused** |
| Added (`read`) to `finish: ready` | 18:34:45 to 18:38:55, **4 min 10 s** | 18:50:29 to 18:54:33, **4 min 4 s** | — |
| Work per second of video | 0.52 | 0.51 | — |
| Doze | deep Doze (`IDLE`) from about 2.5 min in, while the job was at `dedup`; the job went on to `finish` | the same (`IDLE` at about 2.4 min) | — |
| Notification | "Video 1 of 1, eyko85_8min.mp4: split", then dedup, small_objects, latest; gone after `finish` | the same | — |
| Battery | 51 to 49 %, highest 32.5 C | 49 to 47 %, highest 30.6 C | — |
| Stopped by Android? | no stop or kill line while the job ran | no (see note) | `suspended=true`, by `com.google.android.flipendo` (Extreme Battery Saver) |

The two runs give the same output: 1,440 frames, 149 kept by filter, 14 by dedup, 7 small objects found, 79 sightings.
Stage times, run 1: read 1.5 s, split 79 s for frames (18 s of it to JPEG) plus 61 s for audio, filter 7 s, dedup 11 s, scene 16 s, small_objects 33 s, embed_texts 1 s, latest 41 s.

Note on run 2's system lines: the two "Killing com.eykon.memory" and "app died" lines at 18:49:53 come from the script's own fresh start of the app (`am start -S`), 36 s before the clip was added. The "Binding died" line at 19:00:31 is WorkManager's remote connection closing six minutes after the job finished.

## Answer for G10

**Yes, a long clip finishes with the app in the background**, the phone locked and in deep Doze, with or without Battery Saver: 8 minutes of video in about 4 minutes. The running foreground service keeps it going and shows progress.
**The Android limit that stops it is Extreme Battery Saver.** It pauses Eykon completely: the app cannot be opened, and a job cannot run until it is turned off. What happens to a job already running when Extreme Battery Saver is switched on was not tested.

## Seen, not acted on

- Splitting 480 s of audio took 60-61 s, against 5.4 s for a 75 s clip earlier today (about 8x per second of audio). This was not looked into.
- This is a Pixel result. The Infinix (Android 13, a different maker's power manager) was not run.
