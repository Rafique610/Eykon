# Phone vector speed sweep, 1k to 300k (EYKO-95)

Protocol written 5 November 2026, before any controlled run. Cool run done 7 November (Infinix X670).
Hot run done 7 November (with a late start, see below). Low-battery run is **not done yet**. Supervisor questions answered: B1 "one run? spread?", B2 "why only 20k?",
B4 memory, B6 "does a hot phone slow down?".

## Protocol (fixed before the runs; not changed after seeing numbers)

Every phone follows these rules, so the lead's Pixel and A32 runs can use them too.

**Before each session**
- Battery at least 80 % for the cool and hot runs.
- Phone **unplugged** while the test runs.
- Flight mode on, screen on and unlocked, other apps closed (cleared from recents).
- Room temperature written down. Battery level and temperature read with `adb shell dumpsys battery`
  before and after each run (temperature is in tenths of a degree C).
- Test build: phone kit 2026-11-03, `-e commit a637e1d` (from `KIT-VERSION.txt`).

**Runs**
1. **Cool run:** sizes 1k, 5k, 20k, 50k, 100k, 300k. The test does 5 runs per size.
2. **Hot run:** play a video or run the video pipeline for 10 minutes, then sizes 20k and 100k.
3. **Low-battery run:** sizes 20k and 100k at 30 % battery or less.

**Command** (after `adb logcat -G 16M` and `adb logcat -c`):

```
adb shell am instrument -w -e class com.eykon.memory.spike.VectorStorageSpikeTest#blobColumnWithBruteForceSearch -e sizes <list> -e commit a637e1d com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
```

**Recording**
- The CSV the test writes on the phone is pulled and saved unedited (shared format; it records battery
  level, temperature and memory for each row).
- The logcat (`adb logcat -d -s EYKO31`) is saved raw next to it.
- If the phone runs out of memory at a size, that is a result: record the size and the error.

**Not controlled by this protocol:** the Pixel's 97 %-full storage (gap G18, EYKO-83) and the phone's
Android version.

## Results: Infinix X670, cool run (7 Nov 2026, 13:10 to 13:16)

Session facts: Infinix X670, Android 13, platform SQLite 3.32.2, kit commit a637e1d, vectors are 512-dim
random unit vectors (`random_unit_seed31`). Battery 90 % at the start, 89 % at the end. Phone **unplugged for
most of the run, not all of it**: the test was started over USB at 13:10:47 with `setsid nohup`, and the cable
was pulled some time after that (exact time not recorded). The 1,000 and 5,000 sizes finished within about
10 seconds of the start, so they ran with the cable in; later sizes ran on battery. The run kept going after
the cable was pulled and finished 13:16:47. Flight mode on, apps cleared, screen on. Room temperature 27 C (told by Zara,
not measured). Battery temperature 30.3 C at the start, 32.9 C at the end. 5 runs per size.
Raw files: `docs/results/vectors/infinix-2026-11-07-cool.csv` (pulled unedited) and
`docs/results/vectors/proof/infinix-2026-11-07-sweep-cool-logcat.txt` (raw `logcat -s EYKO31`).

Three search methods are in the test: **disk** = read every vector from SQLite on each query (the app's
original way), **memory** = vectors already in a Java array, plain loop (the app's way), **fast** = in-memory
with a faster loop (its top-20 matched the app's loop in 400 of 400 checks at every size).

Median of the 5 run medians in ms (range of the 5 in brackets). Slowest p95 of any run in the last column.

| n | disk | memory | fast | worst p95 (memory) | peak PSS (MB) |
|---|---|---|---|---|---|
| 1,000 | 21.3 (18.8 to 23.1) | 2.3 (2.3 to 2.4) | 0.8 (0.8 to 0.9) | 3.0 | 222 |
| 5,000 | 142.2 (141.6 to 142.7) | 12.5 (12.4 to 12.7) | 3.6 | 18.2 | 69 |
| 20,000 | 1,100.2 (1,096.6 to 1,107.3) | 56.4 (55.6 to 57.3) | 13.9 | 63.6 | 103 |
| 50,000 | skipped (over 20,000 limit) | 160.0 (159.2 to 161.0) | 34.4 | 166.5 | 162 |
| 100,000 | skipped | 354.0 (351.4 to 355.6) | 69.1 (68.8 to 69.5) | 371.3 | 252 |
| 300,000 | skipped | **OutOfMemoryError** (needed a 614 MB array, Java heap limit 268 MB) | not reached | n/a | n/a |

Where each method crosses 200 ms (median):
- **disk:** between 5,000 (142 ms) and 20,000 (1,100 ms). Not measured in between.
- **memory (the app's way):** between 50,000 (160 ms) and 100,000 (354 ms). Not measured in between.
- **fast:** not within 100,000 (69 ms). 300,000 could not be tested (out of memory), so its crossing is unknown.

What the numbers say:
- **Spread:** the 5 runs agree closely (memory 20,000: 55.6 to 57.3 ms; 100,000: 351.4 to 355.6 ms). The
  first run of a size is sometimes slower on disk (1,000: 18.8 to 23.1 ms). This answers B1 for the cool phone.
- **300,000 vectors fail on this phone** with the same Java-heap OutOfMemoryError as the EYKO-94 memory test,
  so the 300k answer does not depend on speed.
- **Heat:** the battery rose 2.6 C during the run (30.3 to 32.9) with no sign of a slowdown inside a size
  (memory 100,000 runs: 351.9, 351.4, 355.7, 355.6, 354.0 ms). A real hot-phone test is still to do.
- **Odd:** disk read at 20,000 (1,100 ms) is 7.7 times the 5,000 time for 4 times the vectors, more than
  linear. I did not investigate why (it could be the SQLite page cache; not tested).
- Peak PSS of 222 MB at n = 1,000 is the first run of the first size (JIT and start-up), not the data.

## Results: Infinix X670, hot run (7 Nov 2026)

**Heat load:** the video pipeline processed 6 clips (the Snapchat clip, both PXL clips 094359 and 094903, and
three other short phone clips of 20, 30 and 30.5 s) from 13:31 to 13:42:40 (about 11 minutes), with the phone unplugged from the laptop's side only for the sweep
(it was on USB during the load). Battery temperature read each minute (`infinix-2026-11-07-hot-load-readings.txt`):
32.0 C at 13:34, 37.3 C peak at 13:39, 36.5 to 37.2 C until the load ended, battery 89 to 88 %.
**Deviation from the protocol:** my laptop shut down during the load, so the sweep did not start right
after it. It started at 13:52:25, **10 minutes after the load ended**, when the phone had already cooled to
35.6 C. So this is a "warm" run (35.6 to 36.6 C during the sweep, against 30.3 to 32.9 C in the cool run),
not the peak 37.3 C. The sweep was started over USB at 13:52:25 and the cable was pulled shortly after (time not recorded), so the
start of the 20,000 size may have run with the cable in. Flight mode, battery 88 %, room 27 C. Files:
`infinix-2026-11-07-hot.csv` and `proof/infinix-2026-11-07-sweep-hot-logcat.txt` (raw).

Median of the 5 run medians in ms, hot against cool:

| n | method | cool | hot (35.6 to 36.6 C) | change |
|---|---|---|---|---|
| 20,000 | disk | 1,100.2 | 1,144.0 | +4 % |
| 20,000 | memory | 56.4 | 55.9 | -1 % |
| 20,000 | fast | 13.9 | 14.0 | 0 % |
| 100,000 | memory | 354.0 | 352.2 | -1 % |
| 100,000 | fast | 69.1 | 68.8 | 0 % |

Answer to B6 ("does a hot phone slow down?"): **not measurably here.** Memory and fast search are within 1 %
of the cool run; only disk read at 20,000 is slower (+4 %, 1,142 to 1,154 ms against 1,097 to 1,107 ms, so the
ranges do not overlap). The phone only got 5 C warmer, and the sweep ran 10 minutes after the peak, so a
hotter phone could still throttle; that was not tested.

## Other phones (the lead's earlier runs, not under this protocol)

Files `pixel9proxl-2026-11-04-sweep-real.csv` and `a32-2026-11-04-sweep-real.csv`. They were run on 4 Nov,
before this protocol, with a different build (`290c200-eyko100`), real clip vectors plus noise instead of
random vectors, and a disk limit of 5,000 instead of 20,000 (so disk is missing from 20,000 up). The Pixel
run started at 55 % battery. Only the shape is comparable, not the exact times. Median ms:

| n | Infinix memory | Pixel 9 Pro XL memory | A32 memory | Infinix fast | Pixel fast | A32 fast |
|---|---|---|---|---|---|---|
| 1,000 | 2.3 | 1.6 | 3.1 | 0.8 | 0.6 | 1.2 |
| 5,000 | 12.5 | 8.6 | 16.2 | 3.6 | 2.5 | 4.9 |
| 20,000 | 56.4 | 37.5 | 81.8 | 13.9 | 7.9 | 18.6 |
| 50,000 | 160.0 | 101.6 | 245.9 | 34.4 | 19.6 | 45.8 |
| 100,000 | 354.0 | 261.6 | 536.8 | 69.1 | 38.8 | 91.0 |

The Infinix sits between the Pixel and the A32 (about 1.4 times the Pixel and 0.65 times the A32 on
memory). On the app's way, 200 ms is crossed between 50,000 and 100,000 vectors on the Infinix, between
50,000 and 100,000 on the Pixel (101.6 then 261.6) and between 20,000 and 50,000 on the A32
(81.8 then 245.9). Disk read at 5,000: Infinix 142 ms, Pixel 238 ms, A32 250 ms (the Infinix is faster
here; cause unknown, the builds differ).

## Not done yet

- **Low-battery run** (20,000 and 100,000 at 30 % or less).
- A hot run that starts straight after the load, at the peak temperature.
- Pixel and A32 runs under this protocol (the lead's phones).
- Sizes between 50,000 and 100,000 (to find the 200 ms crossing more exactly).
- Device sheet for the Infinix is in `docs/results/vectors/proof/infinix-2026-11-05-device.txt`; the lead's
  sheets for the other two are in the same folder.
