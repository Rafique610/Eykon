# Decision re-check: ten proposals tested (26 Nov 2026)

On 26 Nov the lead (Taha) asked for every current decision to be checked against its own reasons, and for each proposed
better way to be **tested**: adopt it if the test holds, and write it down here if it does not, so later sessions know the
path was tried. This file is that record. Each part gives the proposal, the test (exact command, data, device), the numbers,
and a one-line verdict. Base: `feature/video-memory` at `5024d67` (27 Nov: merged with `9218820`); branch `taha/decision-recheck`.

Phone runs: Zara's **Infinix X670 (Android 13)**, over USB, a second copy of the app installed beside hers
(`-PidSuffix=.recheck`, package `com.eykon.memory.recheck`), so her own app and data were never touched. Laptop: Intel
i5-10310U, ONNX Runtime 1.31.1 (the app's version). The Pixel and the A32 were not used (rule in `processes.md`: the
Infinix answers these; where only the slowest phone could settle a point, that is said below).

## Verdicts at a glance

| # | Proposal | Verdict | What changed |
|---|---|---|---|
| 1 | Drop repeat frames only against the last W s, not the whole video | **Not supported**: our 75 s clips, and EYKO-132 on long still clips and EPIC | nothing |
| 2 + 3 | Search an int8 copy first, then exact float32 for the best candidates and window neighbours | **Exact on the laptop** (52 of 52 identical and certified, 53 MB read instead of 205 MB); **phone speed not measured** | ADR 0001 note only; search unchanged; NEON kernel waits on `taha/recheck-phone-pending` |
| 4 | Give the mapped vector pages back when the app's screen is hidden | **Mechanism holds on Linux** (PSS 219 → 23 MB, same scores); **never run on a phone** | **not merged**: code waits on `taha/recheck-phone-pending` for the kill test |
| 4b | (found while checking ADR 0001's MAX(id) rule) a split-stage rerun leaves deleted vectors in the search file | **Bug confirmed on the phone** (20 rows in the file for 15 live) and **fixed** (15 for 15) | **adopted**: `VideoSplit.clearEarlierRun` |
| 5a | Same-object rule using time (same clip within T s) | **Refuted**: 17 to 59 wrong calls against 14 today | nothing |
| 5b | Move the crop vector out of the sightings row | **Refuted**: 4,212 against 4,122 B a sighting; 16 KB pages (EYKO-167) are what helps | nothing |
| 6 | A separate vector file with 16 KB pages instead of converting with VACUUM | **Refuted**: own file stays 4 KB; ATTACH gives 16 KB but Android then turns WAL off | nothing; VACUUM conversion stays (EYKO-175) |
| 7 | Accelerators for the models (XNNPACK, NNAPI; a GPU run for the VLM) | **Not tested**: no completed phone run | nothing; open |
| 8 | Drop YOLOX-Tiny beside D-FINE (EYKO-134) | **Not supported**: YOLOX alone finds 75 of 1,400 COCO objects (and makes 85 wrong boxes). The one-open-vocabulary-detector variant: not tested | nothing |
| 9a | Hybrid search per channel (keywords for transcripts) | **Not testable yet**: no transcripts exist (EYKO-7/8) | recorded here for decision D2 (EYKO-75) |
| 9b | One "not found" cut-off on the best score (EYKO-138) | **Refuted** on COCO: about 25 % wrong calls (fixed or relative cut-off) | nothing; EYKO-138 needs another signal |
| 10 | Many Ego4D gains may be inside the noise | **Holds**: R@1 window gain, any-object crops (per set), smoothing ±6 s and the 0.85 choice are not shown | per-question results are now saved (`ego4d_eval.py`) |

## 1 · Repeats against the whole video, or only recent frames

**Proposal.** `VideoDedup.kt` drops a frame within 6 hash bits or cosine 0.95 of *any* unique frame so far. Coming back to the
same view later is the evidence that a thing is still there, so compare only with the last W seconds.

**Test.** `task dedup-window -- <clips>` (`src/benchmarks/dedup_window.py`): the laptop copy of the phone's layers
(`keyframe_tune.py`, the phone's thresholds), on our two kit clips (`PXL_20261014_094359202.mp4`, `..._094903187.mp4`,
75 s each, sha256 as in the kit). Every filtered frame goes through D-FINE S (0.5, no person) and YOLOE-11L (keys, earbuds,
0.25) with the app's rules; "none" (no dedup) is the reference. Raw: [`dedup-window/dedup-window.json`](dedup-window/dedup-window.json).

| Clip | Frames kept: none / whole / 10 s / 20 s / 30 s | Object names (of 23) whose last sighting is lost: whole / 10 s / 20 s / 30 s |
|---|---|---|
| 094359202 | 134 / 31 / 34 / 31 / 31 | 10 / 6 / 9 / 9 |
| 094903187 | 179 / 53 / 56 / 54 / 53 | 5 / 5 / 5 / 5 |

**Reading.** A 20 or 30 s window keeps the same frames as the whole-video rule (one name differs on one clip): on these clips
no repeat more than 20 s apart was being dropped. Only a 10 s window changes anything (+3 frames, 4 names fewer lost, one
clip). What does lose names is dropping look-alike frames **at all** (5 to 10 of 23 names), because near-identical frames
carry different small detections; a window does not fix that. **Verdict: not supported on 75 s clips; the case it was
about (coming back after minutes) was not on these clips. Nothing changed.**

**Independent test (Rafique, EYKO-132, 27 Nov, [`2026-11-27-dedup-recent-or-whole.md`](2026-11-27-dedup-recent-or-whole.md)),**
with its pass rule written before the run (W = 30 s: at least 12 of 13 events on two long still clips with at most 59
frames, and EPIC recall within 1 point): **fails**. W = 30 s gave 10 of 13 events with 66 frames (whole video: 9 with 58);
EPIC was unchanged at 79.1 %. W = 5 s recovers 12 of 13 but keeps 84 frames. So on a still scene my concern is real (a
short window brings missed events back), but it pays for them in frames; the whole-video rule stays. Neither test measured
"where is it now" answers on a recording where the camera returns after many minutes.

## 2 + 3 · An int8 first pass, exact scores only where needed

**Proposal.** ADR 0001 rules out every top-k index because "the app needs every frame's score" for its windows. But a window
only needs the scores of the hit's neighbours. So: score every row from an int8 copy (one scale per row, phrase quantised
too), take the best M, score those and every neighbour a window looks at exactly in float32, and grow the windows on the exact
scores. A per-row error bound certifies that no row outside the M could beat the weakest window used; if it cannot certify,
M doubles (at worst it is the exact search).

**Test.** `task int8-windows` (`src/benchmarks/vector_int8_windows.py`): 100,000 COCO photo vectors (EYKO-113) cut into
videos of 100 frames 1/3 s apart, plus our own 90 clip frames as one real video; 52 queries (21 COCO captions, 21 EPIC
narrations, 10 own phrases through the app's text model); the app's rule (GROW 0.85, GAP 10 s, HALF 1.5 s, 20 windows).
Raw: [`int8-windows/int8-windows.json`](int8-windows/int8-windows.json).

| What | Result |
|---|---|
| Windows identical to the app's exact search | **52 of 52** queries |
| Certified by the bound | **52 of 52** |
| Float32 rows read per search | median **679**, largest 5,157 (of 100,090) |
| Data read per search | **53 MB** (int8 copy 51.6 MB + float rows) against **205 MB** float32 today |

**Phone: is the int8 pass faster? Not measured.** `Int8PassTest` (NEON `scoreI8` against `scoreF32`, both from mapped files
of the same 100k x 512 rows) was written but the Infinix disconnected before it ran. The NEON kernel compiles and links; it
has **never executed**. Reading less data is shown; being faster is not.

**Verdict: the method is exact on the laptop; whether it is worth having is open.** Search is unchanged. The ADR's "the app
needs every frame's score" no longer rules out top-k methods on correctness grounds (noted in ADR 0001). The kernel and its
phone test are on branch `taha/recheck-phone-pending`, not merged.

## 4 · Hand the mapped pages back in the background

**Proposal.** EYKO-116 found the Infinix kills the app in the background once it holds about 225 to 276 MB of PSS
(40,000 rows x 3 tables and above). Video jobs never search, so when the screen is hidden the mapped pages can be given back
(`madvise(MADV_DONTNEED)` on a read-only shared mapping drops only this process's copy; the next search reads them again).

**Laptop (mechanism).** `src/benchmarks/recheck_release_pages.py`, 100k x 512 float32 (205 MB), raw
[`recheck-release/release-pages-laptop.json`](recheck-release/release-pages-laptop.json): PSS **23 → 219 MB** after a
search, **23 MB** after the release, search after it 16.3 against 19.6 ms, **scores identical**.

**Built, not merged.** On branch `taha/recheck-phone-pending`: `eykonvec.c` `release()` (page-aligned `madvise`),
`VectorNative.release`, `VectorBlock.release`, `VideoVectors.releaseMapped()`, called from
`MemoryApp.onTrimMemory(TRIM_MEMORY_UI_HIDDEN)`. With it the app builds, the 125 JVM tests pass and the library is 16 KB
aligned with all JNI symbols exported. **Never run on a phone**: the Infinix disconnected before the hold test.

**To finish (Infinix, about 15 minutes).** On that branch, with the app and test APKs installed:
`adb shell am instrument -w -e class com.eykon.memory.video.OffHeapVectorTest#holdInBackground -e mode MAPPED_NATIVE -e n 100k -e seconds 300 [-e release true] com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner`
(once without and once with `-e release true`). **Merge if** the run with release survives 300 s with the same pid, its PSS
falls, and the search after it completes. If it is killed anyway (EYKO-116 run 3 was killed at 38 MB PSS), record that the
release does not stop the kill and drop the change. Note the test is a test process, not the installed app.

**Verdict: open.** The memory effect is shown on Linux only; whether it prevents the Infinix kill is unknown.

## 4b · A rerun of the split stage left deleted vectors in the search file (bug, fixed)

**Found while checking** ADR 0001's rule "any code that deletes vectors must call `VideoVectors.forget`". When the split
stage reruns for a video, it deletes the video's frames, and their `image_vec` rows go by `ON DELETE CASCADE`. Later
`embed_images` deletes nothing (the rows are already gone), so it never called `forget`. The file's own check reads only its
first and last rows, so for a video in the middle the deleted rows stayed in `<db>.image_vec.vec`.

**Phone test.** `StaleVectorsTest` (Infinix, three videos, the middle one rerun, the old cleanup and the fixed one):

```
old cleanup:   rows in the search file 20, live rows 15, deleted rows still in the file: [6, 7, 8, 9, 10]
fixed cleanup: rows in the search file 15, live rows 15, deleted rows still in the file: []
```

**Fix.** `VideoSplit.clearEarlierRun`: if the video had image vectors, drop the search file (`VideoVectors.forget`) after
deleting the frames; it is rebuilt at the next search (ADR 0001 already accepts a rebuild on delete). Effect before the fix:
`VideoSearch` skipped the dead ids (it joins on `frames`), so answers were right, but the file grew and `knn()` could return
dead ids. The other fragility raised with this rule, an `UPDATE` of an existing vector going unnoticed, was checked by reading
the code: no code updates a vector in place (`put` is only called after a delete that calls `forget`, or for new ids), so no
counter table was added. Only the split rerun reached vectors by cascade; no code deletes a video today (EYKO-66 will, and
must call `forget`).

**Verdict: adopted.**

## 5 · Sightings: a time rule, and where the crop vector lives

`src/benchmarks/recheck_sightings.py`, raw [`recheck-sightings/recheck-sightings.json`](recheck-sightings/recheck-sightings.json).

**5a.** 54 phone crops with the identities Zara checked (EYKO-72): 44 same-object pairs, 292 different.

| Rule | Same missed | Different merged | Wrong |
|---|---|---|---|
| **App: cosine ≥ 0.87** | 11 | 3 | **14** |
| same clip within 2 s, else 0.87 | 11 | 6 | 17 |
| same clip within 5 s | 7 | 23 | 30 |
| same clip within 10 s | 6 | 41 | 47 |
| same clip within 30 s | 4 | 55 | 59 |
| scene-sized crop (≥ 480 px) in the same clip | 5 | 8 | 13 |

Different objects with the same name are often seconds apart (40 of 292 pairs within 10 s), so time without box overlap
merges them. The scene-sized rule's 13 against 14 is one pair: noise. **Verdict: refuted.** A rule with box overlap
(tracking) could not be tested: the saved crops have no boxes.

**5b.** 20,000 rows of the `object_sightings` shape: 4 KB pages 4,122 B (vector in the row) against 4,212 B (side table);
16 KB pages 2,360 against 2,450 B. **Verdict: refuted**: the waste is a 2 KB value on 4 KB pages; 16 KB pages fix it.

## 6 · A separate 16 KB vector file instead of VACUUM

`VectorPageSizeTest#aSeparateFreshFileFor16KbPages` (Infinix):

```
separate file, own_file: page_size 4096, journal truncate
separate file, attached: page_size 16384, journal delete, main journal truncate
```

Both lines are from the phone, with the app-style database opened by the framework helper and
`enableWriteAheadLogging()` called before the ATTACH (`main journal truncate` is what it read after the ATTACH; EYKO-175
showed the same helper reads `wal` on this phone). The AOSP source explains the result.

A file opened on its own with Android's `SQLiteDatabase` keeps 4 KB (Android sets up the file when it opens it, before our
PRAGMA). ATTACHed, it gets 16 KB, but Android then switches the app's database out of WAL: AOSP
`SQLiteDatabase.executeSql` calls `disableWriteAheadLogging()` on the first `ATTACH`
([source](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/main/core/java/android/database/sqlite/SQLiteDatabase.java),
`if (statementType == DatabaseUtils.STATEMENT_ATTACH) { … disableWriteAheadLogging(); }`), and `enableWriteAheadLogging`'s
own text says "If the database has any attached databases, then execution of queries in parallel is NOT possible". The app
needs WAL so the video worker writes while the screen reads. **Verdict: refuted; converting once with VACUUM (EYKO-175,
412 → 235 MB in 13.9 s at 100k on this phone) stays the route.**

## 7 · Accelerators for the models

**Not tested.** `ModelAcceleratorTest` (each of the five ONNX models with the app's CPU setting, XNNPACK and NNAPI; median of
10 runs and the largest output change) is written. On the Infinix its first run skipped every model (the copied model files
were not readable by the second app); the second run, after fixing the permissions, did not finish: the phone disconnected.
**No timing was obtained, so there is no verdict.** The other half of the proposal, one GPU run of the VLM on the Pixel
(for EYKO-26 / EYKO-33), was not attempted: no Pixel here. Test on branch `taha/recheck-phone-pending`:
`adb shell am instrument -w -e class com.eykon.memory.video.ModelAcceleratorTest -e runs 10 <test package>/androidx.test.runner.AndroidJUnitRunner`,
then `adb logcat -d -s EYKO_ACCEL`.

## 8 · Is YOLOX-Tiny needed beside D-FINE? (EYKO-134)

`task yolox-beside-dfine -- instances_val2017.json` (`src/benchmarks/yolox_beside_dfine.py`): the 300 COCO val photos of
EYKO-121, the app's rules for both models, against COCO's person-drawn boxes. Raw:
[`yolox-beside-dfine/yolox-beside-dfine.json`](yolox-beside-dfine/yolox-beside-dfine.json).

| Of 1,400 labelled objects (people aside) | Found |
|---|---|
| YOLOX-Tiny (same name, IoU ≥ 0.5) | 529 |
| D-FINE S (any name, IoU ≥ 0.5) | 727 |
| Either (the app today) | 802 |
| **Only YOLOX: lost if it is dropped** | **75** (tennis racket 8, umbrella 7, suitcase 7, bottle 7, book 6, …) |
| YOLOX boxes matching nothing and no D-FINE box | 85 of 721 |

People count (168 photos with people): D-FINE's own "person" is a little better on COCO (mean error 0.62 against 0.73; misses
everyone in 2 photos against 10), but it called keys a person on our own clips, which is why the app counts with YOLOX.
The other variant in the proposal, one open-vocabulary detector (YOLOE-S or L with the full word list) replacing two
models, was **not tested**: it needs a word list for D-FINE's classes, a YOLOE-S export and person-labelled own frames
(EYKO-78).

**Verdict (for dropping YOLOX): not supported.** Dropping YOLOX loses 75 right finds to save the cheapest model (about 35 ms of the scene step's
~320 ms on the laptop). COCO is YOLOX's own training set, so the real check is on person-labelled own clips (EYKO-78).

## 9 · Search: hybrid per channel, and a "not found" cut-off

**9a.** Keywords lost on Ego4D because our captions are built from the detector's word list (EYKO-61). Transcripts (names,
numbers) are where keywords usually win, but no transcript exists yet (EYKO-7/8). **Not testable now**; the proposal (pictures
dense only, transcripts hybrid) is recorded here for decision D2 (EYKO-75), to be tested when speech lands.

**9b.** `task not-found-cutoff -- instances_val2017.json` (`src/benchmarks/not_found_cutoff.py`): 78 COCO names typed as
phrases, best score over 300 photos with the thing ("present") and with those photos taken out ("absent"). Raw:
[`not-found/not-found.json`](not-found/not-found.json).

| Cut-off | AUC | Wrong calls at the best cut-off (of 156) |
|---|---|---|
| Fixed score (0.202) | 0.83 | 38: 22 present hidden, 16 absent answered |
| Relative (best score in standard deviations above that phrase's usual score, 4.29) | 0.80 | 39 |

**Verdict: refuted**: one score cannot say "not seen" reliably (about one call in four wrong). EYKO-138 needs a second
signal (for example a detector naming the thing in the best frames). Nothing changed.

## 10 · How sure are the Ego4D numbers?

`task score-intervals` (`src/benchmarks/score_intervals.py`) reads only our saved totals in `docs/results/ego4d/` (no Ego4D
data is touched: licence, EYKO-139). Raw: [`score-intervals/score-intervals.json`](score-intervals/score-intervals.json).
Wilson 95 % intervals for every score, and for each adopted change the **best-case** exact McNemar test (the files keep
totals only, so it assumes every question that passed before still passes; no real split can give a smaller p).

| Change (card) | Set A | Set B | A + B pooled |
|---|---|---|---|
| Windows, R@1 tIoU 0.3 (EYKO-58) | 8 → 13 of 78, p ≥ 0.06 | 4 → 8 of 32, p ≥ 0.13 | 12 → 21 of 110, p ≥ 0.004 |
| Windows, R@5 tIoU 0.3 | 16 → 25, p ≥ 0.004 | 9 → 12, p ≥ 0.25 | 25 → 37, p ≥ 0.0005 |
| Grow 0.85 instead of 0.8 / 0.9 | ±1 question | ±2 | not shown |
| Any-object crops, last seen (EYKO-62) | 14 → 18 of 39, p ≥ 0.13 | 8 → 12 of 35, p ≥ 0.13 | 22 → 30 of 74, p ≥ 0.008 |
| Wearer prompts + ±6 s, found (EYKO-60) | 9 → 20 of 50, p ≥ 0.001 | 14 → 18 of 49, p ≥ 0.13 | 23 → 38 of 99, p ≥ 0.0001 |
| Smoothing 0 → ±6 s, R@1 tIoU 0.5 | 4 → 2 | 2 → 2 | 6 → 4: not shown |

**Verdict: holds.** On one set alone, only the window R@5 gain and the action wording on set A can be real. Pooled, the
windows, any-object crops and the wording *may* be real (they need per-question results to be sure). The ±6 s smoothing
and the choice of 0.85 over 0.8 or 0.9 are not shown by anything we have. Intervals are wide: hit@1 24.4 % is 16 to 35 %,
last-seen 46.2 % is 32 to 61 %. **Changed:** `ego4d_eval.py` now saves each question's pass or fail (`per_question`, keyed by
clip and index, no Ego4D text), so the next licensed run (after EYKO-139) can be tested question by question.

## Limits

- One phone (Infinix, Android 13). The A32 was not needed for these questions except the background kill, where EYKO-116
  only ever ran on the Infinix too.
- COCO photos stand in for frames in 2 + 3, 8 and 9b; our own long first-person recordings do not exist yet (EYKO-50).
- 1's own run rests on two 75 s clips (EYKO-132 adds two long still clips and EPIC); 5a on 54 crops from one session.
- The phone ran a second copy of the app (`com.eykon.memory.recheck`), the same code, not Zara's installed build.
- **Still open, all needing a phone:** 2 + 3 (int8 pass speed), 4 (background kill), 7 (accelerators). The code and tests
  for them are on `taha/recheck-phone-pending`.
- A TECNO phone connected on 27 Nov had USB debugging off, so nothing ran on it.
