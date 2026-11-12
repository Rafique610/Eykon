# EYKO-111: the chosen vector setup under real conditions (A32 hot, Pixel low battery)

Run 8–9 Nov 2026 by Rafique (phone holder). Checks ADR 0001 (`docs/adr/0001-vector-storage.md`) against its revisit
triggers 1 and 2. Gap G20; supervisor questions B4, B6, B7.

**Verdict:** in every run on both phones, `MAPPED_NATIVE` (the app's default since EYKO-115) gave scores **bit-identical**
to `HEAP_F32` (20 of 20 queries, recall@20 1.0, at 20k, 50k and 100k) and was **never more than 10 % slower** than it.
The worst case was 7 % slower, at 20k and 50k on the hot A32. On the Pixel it was **2.4 to 2.9 times faster**. Trigger 1
did not fire. **Trigger 2 (background kill) was not tested.** The owner closed the run list early (see "Not run").

## Method

- Build: `feature/video-memory` at `5555e3e`, both APKs installed with `adb install -r` (app data kept). The Pixel had the 4 Nov
  build and was updated. Gradle reported the A32 APKs up to date, so they match `5555e3e`.
- Test: `OffHeapVectorTest#speedAndAnswers -e modes HEAP_F32,MAPPED_NATIVE -e sizes 20k,50k,100k -e runs 5 -e commit 5555e3e`.
  512-d vectors `real_own_clips_90+noise`, seed 31, 20 timed queries per run. `HEAP_F32` is the old in-memory way without `COUNT(*)`.
- EYKO-95 protocol as in EYKO-112: started from a 60 s `nohup` timer on the phone (`scripts/eyko111_run.sh start <condition>`),
  cable pulled and flight mode on before the start, screen on, apps cleared. Battery and temperature read before and after.
- New in this run: **CPU clock** read every 5 s from `/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq` (`*-cpufreq.txt`).
  On the Pixel, the phone's own battery history (`dumpsys batterystats --history`) gives the exact plug and power-saver times (`*-powerhistory.txt`).
- Table cells: median of the 5 run medians in ms, with the range of the 5 in brackets. Ratio = `MAPPED_NATIVE` / `HEAP_F32`.

## Samsung A32 (SM-A325F), hot

Warm-up: both kit clips through the app's video pipeline, 00:03:50–00:14, battery 34.3 → 38.1 C (`a32-2026-11-09-eyko111-hot-warmup.txt`).

**hot2** (clean, the one to quote): timer 00:25:45 at 37.4 C, run 00:26:45–00:30:43, battery 42 → 41 %, 34.9 C in the rows.

| n | HEAP_F32 | MAPPED_NATIVE | ratio | identical |
|---|---|---|---|---|
| 20,000 | 19.9 (19.8–19.9) | 21.2 (21.1–21.3) | 1.07 | 20/20 |
| 50,000 | 48.3 (48.2–48.4) | 51.9 (51.6–53.9) | 1.07 | 20/20 |
| 100,000 | 131.3 (131.2–131.3) | 112.1 (111.9–112.7) | 0.85 | 20/20 |

**hot** (hotter, partly spoiled): timer 00:16:00 at **38.9 C**, run 00:17:00–00:21:36, 37.0 C in the rows. A video job the user had
re-added was still queued. It resumed **inside the test process** and ran its last stages from 00:17:02 to 00:18:41, at the same time as the
20k and 50k rows (PSS about 1 GB, models loaded). The 100k rows ran after it finished.

| n | HEAP_F32 | MAPPED_NATIVE | ratio | identical | note |
|---|---|---|---|---|---|
| 20,000 | 32.3 (22.9–46.0) | 22.5 (18.5–68.2) | 0.70 | 20/20 | overlaps the pipeline |
| 50,000 | 66.5 (66.3–71.3) | 57.4 (52.9–57.6) | 0.86 | 20/20 | overlaps the pipeline |
| 100,000 | 131.7 (131.6–131.8) | 113.7 (113.0–113.8) | 0.86 | 20/20 | clean |

**warm** (8 Nov 23:50, not a protocol condition): meant as hot, but there was no real load first (33.8 C, falling). Ratios 0.97 / 0.97 / 0.87, 20/20 identical.

## Pixel 9 Pro XL, low battery

| n | HEAP_F32 | MAPPED_NATIVE | ratio | identical | run |
|---|---|---|---|---|---|
| 20,000 | 8.1 (8.0–8.5) | 3.2 (3.0–3.6) | 0.40 | 20/20 | saver off |
| 50,000 | 20.0 (19.9–20.1) | 8.1 (7.1–8.8) | 0.41 | 20/20 | saver off |
| 100,000 | 39.5 (39.4–39.7) | 13.8 (13.4–14.1) | 0.35 | 20/20 | saver off |
| 20,000 | 8.3 (8.3–8.5) | 3.2 (3.0–3.5) | 0.38 | 20/20 | saver on (lowbat2) |
| 50,000 | 20.6 (19.7–21.5) | 7.7 (7.3–8.1) | 0.37 | 20/20 | saver on (lowbat) |
| 100,000 | 40.2 (40.0–40.4) | 14.9 (14.3–15.1) | 0.37 | 20/20 | saver on (lowbat) |

- **saver off** (`lowbat-nosaver`, the clean one): 26 → 25 %, 29.7–30.6 C. Unplugged 00:49:36, saver turned off by hand 00:49:45,
  run 00:50:20 to about 00:55, plugged back 00:56:21.
- **saver on**: two runs, because each had one size on the charger. `lowbat` (27 %): the charger came out at 00:28:59, 18 s after
  the start, so its 20k rows are partly on the charger. Its 50k and 100k rows are on battery. `lowbat2` (26 %): on battery 00:36:30–00:41:20, so its 20k and
  50k rows are clean, and its 100k rows (00:42:06–00:42:27) ran on the charger. The table takes each size from the run where it was on battery.
- **Power saver made almost no difference** (100k: 13.8 ms off, 14.9 ms on).
- **First search (loads the table)** at 100k: `HEAP_F32` 76–77 s, `MAPPED_NATIVE` 14–15 s (writes the vector file once).

## What the CPU clock shows

- **A32:** in all three battery runs the two fast cores ran at 2.0 GHz for about the first 90 s, then dropped to **1.44 GHz** and stayed
  there to the end. This fits EYKO-112's finding that the A32 is 1.2–1.4 times slower on battery: the phone caps its clock. That is
  three runs on one phone, not a test of the cause.
- **Pixel:** the test runs on one thread, which sits on a 2.6 GHz middle core. The fastest core stayed idle at 700 MHz with power saver
  **on and off**, so the 700 MHz is idling, not a cap. (This corrects a line in the 9 Nov day log.)

## Memory

- A32: `MAPPED_NATIVE` PSS is a little lower than `HEAP_F32` (267 against 288 MB at 100k, hot2).
- Pixel: `MAPPED_NATIVE` PSS is **higher** (432–448 against 304–307 MB at 100k). The mapped file's pages count in PSS while they are
  in RAM, and Android can drop them. The Java heap is what stays small. That is the point of the change (EYKO-115: 5 MB for three tables at 100k).

## Pass marks (written before the runs)

| Mark | Result |
|---|---|
| Bit-identical to `HEAP_F32` in every condition | **Pass**: 20/20 in all 6 runs, every size |
| No more than 10 % slower than `HEAP_F32` | **Pass**: worst 1.07 (A32 hot2, 20k and 50k); Pixel 0.35–0.41 |
| App not killed in the background (A32) | **Not run** |

## Not run (owner's decision, 9 Nov)

The owner stopped the runs after the Pixel run with saver off. Reason: the decision is already supported, and both marks held in every run.
These were not run:

- **A32 low battery** (≤ 30 %), **A32 cool** with this build (the 8 Nov cool run, EYKO-112, used the older kit build and the in-memory method, not `MAPPED_NATIVE`), **Pixel cool and hot**.
- **Background kill** (`holdInBackground`, ADR trigger 2). The only evidence is Zara's Infinix hold (EYKO-109: process kept, first search 3.8 times slower after 5 minutes).

## Things noticed

1. **A queued video job resumes inside the instrumentation process.** `am instrument` starts the app process, and the job queue picks the job
   up. Any phone benchmark must check that `jobs` has nothing `queued` or `running` first. The script does not check this yet.
2. A video the user added on the A32 (recorded 8 Jul 2026, 95 s) **failed three times** with "no frame could be read from the video"
   (one-pass decoding `IllegalStateException`, then frame by frame read nothing). This is a video-intake gap (Head 3), left as it is.
3. The 100k first search still takes 28–31 s on the A32 and 14–15 s on the Pixel for a brand-new library (known ADR cost; in real use the file grows a video at a time).

## Files

- CSVs: `docs/results/vectors/offheap/{a32,pixel9proxl}-2026-11-0{8,9}-eyko111-<condition>-eyko109-speed-*.csv` (pulled unedited).
- Per run under `docs/results/vectors/proof/`: `-device.txt` (battery before and after), `-logcat.txt` (raw `logcat -d -s EYKO109`),
  `-instrument.txt`, `-cpufreq.txt`. Pixel: `-powerhistory.txt`. A32: `-hot-warmup.txt`. Screenshot: `a32-pixel-2026-11-09-eyko111-logcat.png`.
- Runner: `scripts/eyko111_run.sh`.
