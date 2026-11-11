# Background kill with the adopted vector setup, `MAPPED_NATIVE` (EYKO-116 part 1)

Run by Zara Tahir on her Infinix X670, 9 Nov 2026 (22:20 to 00:00). Checks ADR 0001 revisit trigger 2 ("the app is killed in the
background because of the mapped pages"). The pass mark is the ADR's: the process is **not killed** (same pid at the end, and the search
after the hold completes). A slower first search is reported, not failed.

**Result in one line: the pass mark is NOT met at the planned size.** With 100,000 rows x 3 tables, `MAPPED_NATIVE` was killed in 3 of 3
runs, after 187 to 218 s of the 300 s hold. A size sweep puts the line between **30,000 rows x 3 (survived) and 40,000 rows x 3 (killed)**.
The kills look like an app-memory limit set by the phone's vendor power manager, **not** a memory shortage and **not** a fault of the
mapped file as such. That reading is an inference (see "Not tested / limits").

## Setup

| Item | Value |
|---|---|
| Phone | Infinix X670, Android 13, plugged in over USB (battery 65 to 67 %), screen on, flight mode off. The A32 was not run. |
| Build | `feature/video-memory` code at `43d610e` plus the native library: `libeykonvec.so` built by `task build-vector-native` (NDK r28c, sha256 `95f1122d...`, 16 KB aligned, JNI symbol exported). App APK sha256 `d26ae28d...`, test APK `5ccfe6a7...`, installed with `adb install -r`. |
| Test | `OffHeapVectorTest#holdInBackground -e mode MAPPED_NATIVE -e n <rows> -e seconds 300`; three tables (image 512, text 384, audio 512 dimensions) of `<rows>` vectors each, scored once, then held 300 s with pid, PSS and Java heap logged every 30 s, then searched again |
| Job queue before each run | empty (checked by `scripts/eyko116_bgkill.py`) |
| Other apps | Runs 1, 2 and the sweep: phone left untouched. Run 3: Zara used the phone (apps not recorded, and she started a minute or two after the hold began because the start message reached her late). |

## Result: killed or not, by size

All rows `MAPPED_NATIVE` unless noted. "Vectors" is the float32 data in the three mapped files.

| Run | Rows x 3 tables | Vectors | PSS during hold | Java heap | Outcome |
|---|---|---|---|---|---|
| 6 | 20,000 | ~113 MB | 170 MB | 9 MB | **survived** 300 s; searches after: image 9 / text 7 / audio 6 ms, same pid |
| 5 (`HEAP_F32` control) | 20,000 | ~113 MB | 183 MB | 134 MB | survived 300 s; searches 42 / 11 / 14 ms |
| sweep 30k | 30,000 | ~170 MB | 225 MB | 10 MB | **survived** 300 s, same pid, searches 6 to 9 ms |
| sweep 40k | 40,000 | ~225 MB | 276 MB | 7 MB | **killed at 267 s** |
| 7 | 50,000 | ~280 MB | 332 MB | 9 MB | **killed at 287 s** |
| sweep 70k | 70,000 | ~395 MB | 443 MB | 13 MB | **killed at 278 s** |
| 1 | 100,000 | ~560 MB | 339 to 535 MB | 5 MB | **killed at 187 s** |
| 2 | 100,000 | ~560 MB | 604 MB | 11 MB | **killed at 211 s** |
| 3 (Zara using the phone) | 100,000 | ~560 MB | 38 to 338 MB | 14 MB | **killed at 218 s** |
| 8 (`MAPPED_F32`, 10 Nov) | 100,000 | ~560 MB | 606 MB | 15 MB | **killed at 194 s** |
| 4 (`HEAP_F32`) | 100,000 | ~560 MB | n/a | n/a | did not load: `OutOfMemoryError` (268 MB Java heap limit) |

What every kill has in common (Android's own `dumpsys activity exit-info`, saved for the sweep runs):

- `reason=2 (SIGNALED) subreason=0 (UNKNOWN) status=9`, description empty, `importance=125` (a cached, empty process). The system's
  memory killer would be recorded as a low-memory kill; none is.
- `system_server` sends the signal (`Process: Sending signal. PID: ... SIG: 9`). The only log line within 20 ms before every kill is
  `Griffin/StateProvider getAppsArrayRecommend` (Griffin is the Transsion/Infinix power manager).
- Memory was not short: the Java heap stayed under 15 MB, and the PSS was flat.
- In run 3 the PSS dropped from 338 MB to 38 MB at 60 s (the system took the mapped pages back) and the process was still killed at 218 s.
- The time to kill is shorter for larger data (187 to 218 s at 100k, 267 to 287 s at 40k to 70k) but not strictly in order (70k at 278 s came before 50k at 287 s).

## Reading

1. On this phone the process is killed once it holds more than about **225 to 276 MB of PSS**: between 30,000 and 40,000 rows x 3 tables,
   about **170 to 225 MB of vectors**. Below that line the whole 300 s passes and the first search after the hold is as fast as before.
2. The planned size of 100,000 rows x 3 tables fails the ADR's pass mark three times out of three. ADR 0001 trigger 2 has fired for
   large tables.
3. It is not evidence against the mapped file in itself: the plain heap copy cannot load 100,000 x 3 at all (run 4), and at 20,000 both modes
   behave the same (runs 5 and 6). The mapped file is what lets the larger sizes load; the phone then kills the process that holds them.
4. A design that stays below about 200 MB of vectors per process (roughly 35,000 rows across three tables of this shape on this phone)
   passed every time. **Decision (Rafique, lead, 10 Nov): no vector cap.** The card closes with the result as it stands: Infinix only, the test process (an instrumentation
   process, `importance=125`) and not a normal installed app, and the A32 not run. Run 3 was also killed at 38 MB of PSS, so "about 200 MB" is not a clean threshold; the safe statement is "killed at 40,000 rows x 3 and above".

## This disagrees with EYKO-109; the mode is ruled out, the cause is not known

The EYKO-109 hold (8 Nov, same phone, same 3 x 100,000 rows, 300 s) was **not killed**: pid 22330 stayed, PSS 598 to 567 MB. Today's
three runs of the same size were killed. To test whether the **mode** explains it, I ran EYKO-109's own mode, `MAPPED_F32` (Java
`FileChannel.map`), at 3 x 100,000 rows on 10 Nov (00:15, battery 74 %, plugged in, untouched): **killed at 194 s**, the same way (SIGNALED/9,
PSS 606 MB, `importance=125`, Griffin line just before). So the mode is not the difference.

What did differ from EYKO-109: the day and the phone's state (what the power manager had learnt, how long it had been on), and in EYKO-109
the laptop opened five apps in turn during the hold, which may have changed how the system ranked the test process. Neither was tested here.
All 7 holds at 40,000 rows x 3 or more were killed; none at 30,000 or fewer. The EYKO-109 "not killed" result for 100,000 rows should be
read as "not killed on 8 Nov, under those conditions", not as a guarantee.

## Not tested / limits

- **Who sends the kill is not proven.** Griffin appears in the log before each kill and the exit record names no reason. This is an
  inference, not a measurement. No other apps' memory use was controlled.
- **The test runs in an instrumentation process**, which Android protects more than a normal app, so a kill here is strong evidence but the
  line for a normal installed app may differ (it could be higher or lower). It was not tested from inside the app.
- **No heap comparison above 20,000 rows**: `HEAP_F32` cannot hold more in the 268 MB Java heap.
- **Run 3** was not under controlled conditions (apps used, start time not recorded). **Runs 1 and 2** were run before the prompt could reach
  Zara, so they are "untouched" runs.
- **Failed attempts, kept for honesty:** the first attempt failed at startup because the APK I had built did not contain `libeykonvec.so`
  (`UnsatisfiedLinkError`); rebuilt with the library. An attempt at 20,000 rows was stopped when the phone was unplugged and Android recorded it
  as SIGNALED at 22:57; that is not counted, because the disconnect ends the instrumentation.
- **A32 not run.** One phone only.

## Evidence files

`docs/results/vectors/bgkill/infinix-2026-11-09-run1`, `-run2`, `-run3`, `-run4-heap-100k-oom`, `-run5-heap-20k-control`, `-run6-mapped-20k`,
`-run7-mapped-50k`, `-sweep-30k`, `-sweep-40k`, `-sweep-70k` and `infinix-2026-11-10-mapped-f32-100k`: `device-sheet.txt`, `meminfo-before.txt`, `meminfo-after.txt`,
`eyko109-logcat.txt` (raw `logcat -d -s EYKO109`), `instrument-output.txt`, `kill-moment-logcat.txt` (runs 1 to 3 and 7) and, for the three sweep
runs and `exit-info.txt` (the full all-buffers logs hold other apps, so they are kept off the repo, in `C:\eykon-kit\bgkill-full-logs`; `kill-moment-logcat.txt` is the filtered excerpt). A logcat screenshot is on the EYKO-116 card.
