# ADR 0001: How the phone stores and searches vectors

**Status:** **Accepted** by the owner (Rafique), 8 November 2026. Proposed the same day.
**Decided by:** Rafique (owner and phone holder), with evidence from Taha Ahmed (lead, research) and Zara Tahir (evaluation).
**Card:** EYKO-98 · **Head:** 2 (Setup and storage) · **Supersedes:** the 12 Oct choice "BLOBs loaded into one Java array per table" (EYKO-31).

## Decision

1. **The database stays SQLite, with vectors as float32 BLOB columns** in `image_vec`, `text_vec` and `audio_vec`. These are the same
   tables and bytes as the laptop's `src/video_memory/schema.py`, and they stay the **source of truth**. Raw SQL, no ORM (unchanged).
2. **Search reads a copy of the vectors in a file next to the database** (`<db>.<table>.vec` + `<db>.<table>.ids`). The file is
   memory-mapped and scored in place by a small NEON C function (`libeykonvec.so`, mode `MAPPED_NATIVE`), not loaded into Java memory.
   The file is written once, appended to as videos arrive, and rebuilt if it no longer matches the database.
3. **The "has the table changed?" check on every search reads `MAX(id)`**, not `COUNT(*)`. Writes and deletes clear the cache themselves.
   Any code that deletes vectors must call `VideoVectors.forget`.
4. **If the native library does not load, the app falls back** to the old in-memory search (`HEAP_F32`), which is exact but limited to about 20k rows per table.

In code: `android/app/src/main/java/com/eykon/memory/video/VideoVectors.kt`, `VectorBlock.kt`, `android/app/src/main/cpp/eykonvec.c`
(commit `1a09f2b`, EYKO-114 / 115).

## Why: the problem

- Each vector is 512 numbers (image) or 384 (text). Search compares the question with **every** row. The app needs every frame's
  score, not just the top 20, because it grows time windows around the best frames.
- Android gives each app **268 MB of Java memory**, on the 6 GB A32 and the 16 GB Pixel alike. With all three tables held in Java
  memory, **20k rows each fit and 50k do not** (`OutOfMemoryError`), on all three phones (EYKO-100, 94).
- Our own target of **200 ms per search on the slow phone has no source yet** (EYKO-101). It is written down as an assumption, not used as a hard limit.

## Options considered (all measured by us unless marked)

| Option | Source / evidence | Result | Verdict |
|---|---|---|---|
| sqlite-vec plugin in Android's own SQLite | EYKO-31, 94 (three phones); EYKO-89: Android builds SQLite with `-DSQLITE_OMIT_LOAD_EXTENSION` (AOSP `external/sqlite/dist/Android.bp`, Android 11 to main) | "no such module: vec0" on every phone | **Impossible** |
| sqlite-vec in Google's bundled SQLite (R1) | EYKO-104 (our own 16 KB, NEON build), EYKO-105 | Works, exact; 3 tables at 100k in 55 MB; **230 ms at 100k vs 91 ms in memory** (A32); at most **4,096 rows** per query (EYKO-108), but the app needs every frame's score | Rejected: 2.5× slower, top-k only |
| sqlite-vec in requery's SQLite (R2) | EYKO-106 | 486 ms at 100k with requery's hard-coded **1 KB pages**; 234 ms with 4 KB pages (same file, both engines within 1 %) | Rejected: same as R1 |
| sqlite-vec compiled into our own SQLite (R4) | EYKO-108 (Zara); same A32 in EYKO-105 | 231 ms at 100k | Rejected: same as R1 |
| sqlite-vec in SQLCipher (R3) | EYKO-89 desk research | Same search plus decryption on every read; no card needs encryption | **Dropped** (owner and lead, 8 Nov) |
| BLOBs read from SQLite on every search | EYKO-31, 95 | 1.1–1.95 s at 20k | Rejected |
| BLOBs in one Java array per table (old way) | EYKO-31, 100, 102 | Exact, fast; **out of memory at 50k** (3 tables) | Kept only as the fallback |
| Direct (`allocateDirect`) buffers | EYKO-109 (Zara, Infinix) | Android counts them in the same 268 MB | Rejected |
| float16 copy | EYKO-109 | Fits 50k; 92.1 % of app hits identical; 8× slower in Kotlin | Rejected: not exact |
| int8 copy + float32 re-score | EYKO-109 | Fits 100k; 97.4 % of app hits identical | Rejected: not exact |
| Memory-mapped float32 file, copied row by row (`MAPPED_F32`) | EYKO-109, 114 | Exact, fits 300k; **+12 to 15 % slower** | Superseded |
| Mapped file, copied 1,024 rows at a time (`MAPPED_BLOCK`) | EYKO-114 | Exact; +8 to 10 % | Superseded |
| **Mapped file, NEON in place (`MAPPED_NATIVE`)** | EYKO-114, 115 | Exact (bit-identical); 3 tables at 100k with **5 MB** Java memory; see below | **Chosen** |
| Approximate index (usearch / HNSW) | EYKO-91 (Taha, laptop; in progress) | Approximate; returns top-k, not every frame's score | Not chosen for now; revisit past the limits below |

## Evidence for the chosen option (Samsung A32, cable in, 8 Nov)

| What | Before (old way, with `COUNT(*)`) | Chosen |
|---|---|---|
| Vector search, 20k rows | 115.2 ms | **21.3 ms** |
| Vector search, 100k rows | 565.2 ms | **102.5 ms** |
| First search after an app restart, 100k | 23.6 s (file rebuilt) | **162 ms** |
| Search after 1,000 new rows, 100k | full rebuild | **151 ms** |
| Three tables at 50k / 100k | out of memory | **loads; Java memory 4 / 5 MB** |
| Same answers | — | bit-identical to the old way, 20/20 queries at every size and after every file step |
| App's own video tests on the phone | — | **OK (55 tests)** |

Files: `docs/results/2026-11-08-mapped-fast.md` (EYKO-114), `docs/results/2026-11-08-adopt-mapped.md` (EYKO-115), CSVs and raw logs under
`docs/results/vectors/offheap/` and `docs/results/vectors/proof/`.

### Under real conditions (EYKO-111, 8–9 Nov, on battery)

`MAPPED_NATIVE` against `HEAP_F32`, same build (`5555e3e`), same phone, same condition. Median ms, then the ratio:

| Phone, condition | 20k | 50k | 100k | Same answers |
|---|---|---|---|---|
| A32 hot (after 10 min of pipeline load) | 21.2 vs 19.9 (1.07) | 51.9 vs 48.3 (1.07) | 112.1 vs 131.3 (0.85) | 20/20 at every size |
| Pixel 9 Pro XL low battery (25–27 %) | 3.2 vs 8.1 (0.40) | 8.1 vs 20.0 (0.41) | 13.8 vs 39.5 (0.35) | 20/20 at every size |

No more than 7 % slower anywhere, so trigger 1 did not fire. Full tables, a second hot run, power-saver runs and CPU clocks:
`docs/results/2026-11-09-final-setup-conditions.md`.

## What we accept (the costs)

- **Extra storage:** the search copy duplicates the vectors, about **205 MB per 100k image vectors** (563 MB for 100k rows in all three tables).
  We keep it because the BLOBs must stay for laptop/phone parity, and the copy can always be rebuilt from them.
- **About 7 % slower than the old way would be** without `COUNT(*)` (102.5 against 95.5 ms at 100k): the price of not running out of memory.
- **A delete rebuilds the whole file** (23 s at 100k). Today only a stage re-run deletes vectors.
- **RAM is still used while searching** (file pages, about 594 MB PSS at 3 × 100k). Android can drop them, and the next search is
  then slower: 3.8× for the first search after 5 minutes in the background, on the Infinix (EYKO-109).
- **arm64 only:** `libeykonvec.so` is built for arm64-v8a. Other phones use the fallback.

## Limits of the evidence

- Speed on battery was measured for **A32 hot** and **Pixel low battery** only (EYKO-111). The owner closed the run list on 9 Nov, so
  **A32 cool and low battery with this build, and Pixel cool and hot, were not run.** On battery the A32 caps its fast cores at
  1.44 GHz after about 90 s, which fits its 1.2–1.4 times slowdown on battery (EYKO-112). That cause was seen but not tested.
- The **background kill** test (trigger 2) was **not run on the A32**. The evidence is the Infinix holds: EYKO-109 (not killed, `MAPPED_F32`, 8 Nov)
  and EYKO-116 (killed at 40,000 rows x 3 and above, `MAPPED_NATIVE`, 9 Nov). They disagree and the reason is not known.
- Only the **vector part** of search was timed. The whole app search (`VideoSearch.frames`, its frames query) is Head 7's (G23).
- Real vectors were our own clips plus noise. Larger real libraries do not exist yet.

## When to revisit this decision

Reopen this ADR if any of these happens:
1. On the A32 hot, A32 low battery or the Pixel, `MAPPED_NATIVE` is **more than 10 % slower than the old way** in the same condition, or
   answers stop being identical (EYKO-112). *Checked 9 Nov (EYKO-111): did not fire.*
2. The app is **killed in the background** on the A32 because of the mapped pages. *Not tested on the A32 (EYKO-111 closed without it). Checked 9 Nov on the Infinix (EYKO-116): **fired for large tables.** `MAPPED_NATIVE` at 3 x 100,000 rows was killed in 3 of 3 holds (after 187 to 218 s of 300); 20,000 and 30,000 rows survived, 40,000 and above were killed. Android records the kills as plain SIGNALED/9, not low memory; the cause (probably the Infinix power manager) is not proven. EYKO-109 on 8 Nov (`MAPPED_F32`, same size) had not been killed, and why is not known. Needs a decision from the owner: `docs/results/2026-11-09-background-kill-mapped-native.md`.*
3. A table passes **300k rows** (the largest size measured, EYKO-109), or one search passes our own 200 ms target on the A32 on battery.
4. The **storage copy** becomes a problem on a real phone (EYKO-83, G18), or "delete a video" (EYKO-66) makes rebuilds frequent.
5. A laptop result (EYKO-91) shows an approximate index keeping recall@20 ≥ 0.99 **and** a way to give every frame a score.

## Not decided here

- Sources for the 200 ms target and the user's library size per month (EYKO-101): an assumption until then.
- The whole-app search speed after a restart (Head 7, G22 / G23).
