# Adopting memory-mapped native vectors: no COUNT(*) per search, vector file written once (EYKO-115)

**Date:** 8 November 2026 · **By:** Rafique · **Card:** EYKO-115 · **Phone:** Samsung A32, cable in · **Builds on:** EYKO-114 ·
**Gaps:** G20 (Head 2), G22 / G23 (Head 7)

**Verdict: adopted, and the vector search is about 5.5× faster.** The app now keeps vectors in a memory-mapped file and
scores them in place with NEON (EYKO-114's `MAPPED_NATIVE`). It falls back to the old in-memory way if the library does not
load. Two costs EYKO-114 found are gone:
1. The `COUNT(*)` change check on every search is now `MAX(id)`.
2. The vector file is written once, then appended to.

On the A32: **102.5 ms at 100k rows** (was 573.8), **21.3 ms at 20k** (was 115.9), and **162 ms** for the first search after a
restart at 100k (was 23.6 s). Every answer stayed bit-identical, the app's 55 video tests pass, and three tables at 100k
still use 5 MB of Java memory.

**The honest cost:** with `COUNT(*)` gone, the old in-memory way would now be **7–8 % faster** than the mapped way (95.5
against 102.5 ms at 100k; 19.9 against 21.3 ms at 20k). Before, that gap was hidden inside the 565 ms. The old way still
runs out of memory at 50k rows, so the mapped way stays.

## What changed (`android/app/src/main/java/com/eykon/memory/video/`)

| File | Change |
|---|---|
| `VideoVectors.kt` | **Change check:** `SELECT IFNULL(MAX(id), 0)` instead of `SELECT COUNT(*), IFNULL(MAX(id), 0)` on every search. The cache is keyed by database file + table, so two databases never share a copy. Writes (`put`), deletes (`forget`) and `clearCache` drop the cache themselves. **Vector file:** `<db>.<table>.vec` (float32 rows) + `<db>.<table>.ids` (int64). On load: if the file ends at `MAX(id)` it is only mapped (read-only); if the table has newer rows, only those are read (`WHERE id > last`) and appended; if the table ends lower, the two files disagree in length (a crash mid-append), or the file's first and last rows differ from the database's (a database made again under the same name), it is rebuilt. **Default mode:** `MAPPED_NATIVE` if `libeykonvec.so` loads, else `HEAP_F32`. An in-memory database (tests) always uses the heap. |
| `VectorBlock.kt` | A read-only mapping for a file that already holds every row. |
| `VideoEmbedImages.kt`, `VideoEmbedTexts.kt` | A stage re-run deletes this video's old vectors with `db.delete(...)`. If any rows went, `VideoVectors.forget` drops the vector file too, so it is rebuilt. |
| `OffHeapVectorTest.kt` (androidTest) | `persistentFile`: every file case above, checked bit-identical against the heap after each step. |

**The rule this relies on:** any code that deletes vectors must call `VideoVectors.forget`. Today only the two embed stages delete
vectors. A future "delete a video" feature (EYKO-66) must call `forget` for all three tables, because the database's `ON DELETE CASCADE`
removes vector rows without passing through `VideoVectors`.

## Results (A32, SM-A325F, Android 13, cable in, battery 100 %, battery 27.2–29.6 C)

**Vector search, the whole `VideoVectors.scores()` call**, median of 5 run medians (range), real own-clip vectors, 20 queries × 5 runs.
All 30 CSV rows match the raw log.

| Rows | EYKO-114 `HEAP_F32` (with `COUNT(*)`) | EYKO-114 `MAPPED_NATIVE` (with `COUNT(*)`) | **Now `MAPPED_NATIVE` (the app)** | Now `HEAP_F32` (not used: out of memory at 50k) |
|---|---|---|---|---|
| 20,000 | 115.2 | 115.9 | **21.3** (21.2–21.4), 5.4× faster | 19.9 (19.8–19.9) |
| 50,000 | 283.7 | 286.2 | **52.1** (51.9–52.2), 5.5× | 48.1 (48.1–48.2) |
| 100,000 | 565.2 | 573.8 | **102.5** (102.2–102.8), 5.6× | 95.5 (95.5–95.6) |

Scores bit-identical to `HEAP_F32` on 20 of 20 queries at every size (recall@20 1.0, 400 of 400). A first run of the same sweep
(CSV kept as reference, its raw log was not captured) gave 21.8 / 52.3 / 103.0 ms, within 0.5 ms.

**The vector file** (`OffHeapVectorTest#persistentFile`, 100k rows, `proof/a32-2026-11-08-eyko115-persist100k-logcat.txt`; 20k in `…-persist20k.txt`):

| Step | 20,000 rows | 100,000 rows | Bit-identical to the heap |
|---|---|---|---|
| First search, writes the file | 1,563 ms | 23,578 ms | — |
| Repeat search | 22 ms | 100 ms | — |
| **First search after a restart** (cache dropped, file reused) | **113 ms** | **162 ms** (was 23.6 s) | 20 / 20 |
| 1,000 new rows added in SQL, **only they are appended** | 67 ms | 151 ms | 20 / 20 (21,000 / 101,000 rows) |
| 10 rows deleted, `forget`, rebuilt | 1,697 ms | 23,210 ms | 20 / 20 |
| Database deleted and made again under the same name, old files left behind | 1,634 ms (rebuilt) | 23,285 ms (rebuilt) | 20 / 20 |

The last row shows the guard works: the old file's first and last rows did not match the new database, so it was not used.

**Memory**, three tables, `MAPPED_NATIVE`: 50k → Java heap 4 MB, PSS 325 MB, 3 of 3 loaded; 100k → Java heap 5 MB, PSS 594 MB, 3 of 3 loaded.

**The app's own tests on the phone:** `VideoSearchTest`, `VideoStorageTest`, `VideoEmbedImagesTest`, `VideoEmbedTextsTest`, `VideoLinkTest`,
`VideoFinishTest`, `VideoLatestTest`: **OK (55 tests)** with the new default (`proof/a32-2026-11-08-eyko115-apptests.txt`).

## Against the pass marks (written before the run)

| Mark | Result |
|---|---|
| Same answers: bit-identical to `HEAP_F32`; the app's video tests pass | **Pass**: 20 / 20 at every size and after every file step; 55 / 55 tests |
| Faster than EYKO-114's `HEAP_F32` (115.2 / 283.7 / 565.2 ms) | **Pass**: 21.3 / 52.1 / 102.5 ms |
| First search after a restart much faster than 23 s at 100k; appending reads only new rows | **Pass**: 162 ms; 151 ms for 1,000 new rows |
| Three tables at 100k with small Java memory | **Pass**: 5 MB |

## Limits and what is still open

- **A delete rebuilds the whole file** (23 s at 100k). That happens only when a stage re-runs on a video that already has vectors, and later when videos are deleted (EYKO-66).
- **The first search of a brand-new library** still writes the whole file (23.6 s at 100k). In real use the file grows a video at a time, by appending.
- **Extra storage:** the file is a second copy of the vectors (about 205 MB per 100k rows of 512 numbers). EYKO-98 decides whether that stays.
- **Measured on the A32 only, on the cable.** Hot, low-battery and Pixel runs are still to do (EYKO-112, EYKO-83). The whole app search
  (`VideoSearch.frames`) was not timed here; only the vector part.
- The `HEAP_F32` column "now" is shown for comparison only. The app does not use it, because three tables do not fit at 50k.

## Files

- CSVs: `docs/results/vectors/offheap/a32-2026-11-08-eyko115-speed-SM_A325F-20261108-1939.csv`, `…-eyko115-memory-SM_A325F-20261108-1942.csv`.
- Raw logs: `docs/results/vectors/proof/a32-2026-11-08-eyko115-speed-logcat.txt`, `…-memory-logcat.txt`, `…-persist100k-logcat.txt`,
  `…-persist20k.txt`, `…-apptests.txt`, `…-logcat.txt` (the first batch, persistence steps), device readings `…-eyko115-device.txt`, screenshot `…-eyko115-logcat.png`.
