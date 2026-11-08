# Route R1: sqlite-vec through Google's bundled SQLite, on the A32 (EYKO-105)

**Date:** 8 November 2026 · **By:** Rafique · **Card:** EYKO-105 · **Phone:** Samsung A32 (the slowest of our three) · **Supervisor questions:** A3, A5, B7

**Verdict: works, not adopted.** Google's bundled SQLite loads our own sqlite-vec build (EYKO-104) on the
A32. It returns exactly the same top 20 as today's search at every size, and three vector tables at 100k
rows stay at about 56 MB of app memory, where today's way runs out of memory at 50k. But it is **2.5×
slower** than today's in-memory search (230 against 91 ms at 100k). It also returns at most 4,096 rows, while
the app needs a score for every frame. On the same phone, Zara's route R4 (her own SQLite build, EYKO-108)
runs at the same speed (231 ms), so no sqlite-vec route makes search faster. The memory problem has a
cheaper fix that stays exact and keeps every frame's score: the memory-mapped file from EYKO-109. The choice
between them belongs to EYKO-98.

## What was tested

- **Route:** `androidx.sqlite:sqlite-bundled:2.7.1`, with `BundledSQLiteDriver().addExtension(<path>/libvec0.so, "sqlite3_vec_init")`
  and the connection opened directly in the test (no Room). Test: `android/app/src/androidTest/java/com/eykon/memory/spike/RouteR1Test.kt`.
- **Plugin:** our own `libvec0.so` from EYKO-104, NEON and no-NEON, copied from the test assets into the
  app's files folder before loading. The phone logged the SHA256 of the file it loaded, and it matched
  EYKO-104 (NEON `264ec326…3e46`, no-NEON `ccd7178d…8329`).
- **Data:** the shared protocol. Real vectors from our own clips plus noise (`real_own_clips_90+noise`),
  1 warm-up + 20 queries × 5 runs, top 20, `vec0` with the default L2 metric. The vectors are unit length, so L2 ranks them like dot product.
- **Reference:** `blob_memory_fast` (EYKO-100's exact in-memory search), same vectors and queries, same process, timed in the same run.
- **Phone:** Samsung A32 (SM-A325F), Android 13, 4 KB pages, 5.9 GB RAM, Java heap limit 268 MB, 53 GB free.
  USB connected, battery 74 → 77 %, battery temperature 29.2 → 30.7 °C (`proof/a32-2026-11-08-route-r1-device.txt`).
  This is not a controlled EYKO-95 protocol run, since the phone stayed on the cable.
- **Build:** the test ran from the working tree on `rafique/eyko-105-route-r1-bundled`, based on `29ac8b5`, before it
  was committed (the CSVs say `29ac8b5+r1test-uncommitted`). The code that ran is the code in the commit that adds this file.

## Load check (claims C1, C3)

From `proof/a32-2026-11-08-route-r1-logcat.txt`:

- `R1 loads: sqlite 3.50.1, vec_version v0.1.9, first open with plugin 10.2 ms`
- `R1 vec_debug: Version: v0.1.9 | … | Commit: e9f598abfa0c06b328d8fe5da9c3760cce74be10 | Build flags:  neon`
- `R1 fts5 works: bm25 = -1.0e-06`

**Correction to EYKO-89:** the bundled SQLite in 2.7.1 is **3.50.1**, not the 3.53.4 found on androidx-main.

## Speed: median ms of the 5 run medians (slowest p95 of the 5 runs in brackets)

Same phone, same vectors, same queries. R1 is this card. R4 is Zara's EYKO-108 test, built by me with the
same NDK r28c and flags and her pinned SQLite 3.53.4 source, and run on this A32 the same afternoon.

| Rows | R1, bundled (NEON) | R4, own SQLite (NEON) | Today: `blob_memory_fast` | R1 against today |
|---|---|---|---|---|
| 1,000 | 3.3 (4.1) | 2.3 (2.5) | 1.2 (1.7) | 2.6× slower |
| 5,000 | 13.2 (19.1) | 13.8 (21.9) | 4.9 (14.0) | 2.7× |
| 20,000 | 53.0 (101.7) | 50.8 (59.5) | 18.5 (18.9) | 2.9× |
| 50,000 | 88.8 (126.8) | 122.3 (161.0) | 45.8 (50.8) | 1.9× |
| 100,000 | **230.2** (233.6) | **231.0** (235.1) | **91.2** (102.3) | **2.5×** |

- **Recall@20 = 1.0000 (400 of 400) at every size**, for R1 and R4 alike (claim A5: same answers).
- **NEON:** without it, R1 is 59.7 ms at 20k and 277.6 ms at 100k (R4: 57.9 and 283.6). That makes NEON
  11–17 % faster. Without NEON the code is not fully scalar, since clang vectorises some loops by itself (EYKO-104).
- **Runs jump between two levels at 50k for both routes** (R1: 124, 124, 89, 88, 88 ms; R4 similar). This
  looks like the phone moving the thread between CPU clusters. It is not explained and was not tested.
  The 100k rows are stable (R1: 229.8 to 230.6).
- **Insert time into `vec0`** (one table): 1k 1.2 s, 20k 9.1 s, 50k 17.5 s, 100k 32.5 s.

## Memory: three tables (image 512, text 384, audio-sized 512), n rows each, one search per table

| Rows each | R1 total PSS before → after | Java heap | Tables searched | Database file | Today (EYKO-100, BLOBs in Java memory) |
|---|---|---|---|---|---|
| 20,000 | 55 → 57 MB | 3 MB | 3 of 3 | 117 MB | fits (A32: 53 → 160 MB) |
| 50,000 | 55 → 58 MB | 3 MB | 3 of 3 | 287 MB | **out of memory** on the 3rd table |
| 100,000 | 55 → 55 MB | 3 MB | 3 of 3 | 574 MB | **out of memory** on the 2nd table |

The vectors stay in the database file and are read from storage on each search. PSS does not count the
operating system's file cache, so "flat memory" means the app holds nothing, not that no RAM is touched.
Only one search per table was timed here; the speed table above is the repeated-search view.

## Size and 16 KB

- **APK added for 64-bit phones:** `libsqliteJni.so` (Google's SQLite) 1,281,456 B plus our `libvec0.so` 145,936 B,
  about **1.43 MB** uncompressed. The artifact also ships armeabi-v7a, x86 and x86_64 copies (1.1–1.25 MB each)
  unless `abiFilters` is set.
- `zipalign -c -P 16 -v 4` on the test APK: **Verification successful**.

## A real cost found while building the test

`androidx.sqlite:sqlite-bundled:2.7.1` needs `androidx.sqlite:sqlite:2.7.1` for its driver API. The Android Gradle
plugin forces a test to use the **same library versions as the app**, and the app is on 2.4.0 through Room 2.6.1.
The first build failed (`Unresolved reference 'SQLiteStatement'`; the dependency report shows
`androidx.sqlite:sqlite:2.7.1 -> 2.4.0`). So even testing R1 meant raising the app's `androidx.sqlite`
from 2.4.0 to 2.7.1 on this throwaway branch (`android/app/build.gradle.kts`). Room stayed at 2.6.1, and the
app built and installed. Adopting R1 in the app would cost more than this: the Room 2.8 step (C4).

## Claims from the research

| Claim | Result | Evidence |
|---|---|---|
| C1: loads sqlite-vec without any Room change | **True for loading**, but the app's androidx.sqlite had to move 2.4.0 → 2.7.1 just to build the test | logcat load lines; section above |
| C2: lowest risk, because Google maintains it | Not tested here (a maintenance claim) | EYKO-89 sources |
| C3: brings FTS5 and `bm25()` | **True** | `R1 fts5 works: bm25 = -1.0e-06` |
| C4: adopting it needs Room 2.6.1 → 2.8.x | **Not tested**: card step 6 runs only if the verdict is "adopt" | — |

## Against the card's pass marks (written 8 Nov, before the run)

- **Works:** yes. It loads, `vec_version` = v0.1.9, and recall@20 = 1.0 at every size.
- **Worth keeping:** mark (a), three tables at 50k without running out of memory, **passes**. Mark (b), faster
  than `blob_memory_fast` at 100k, **fails** (230 against 91 ms).
- By the letter of the rule, one mark was enough, so R1 counts as "worth keeping". **That rule was too loose.**
  It let a route that is 2.5× slower pass on memory alone. The honest reading is the verdict at the top:
  R1 fixes memory but loses on speed and on every-frame scores, and EYKO-109's mapped file fixes memory
  without those costs. Both go into EYKO-98, with R1 as the weaker candidate.
- **Pixel and Infinix:** not run. R4 on the Infinix (Zara, EYKO-108) and R1/R4 on the A32 point the same way.
  The Pixel waits for EYKO-83 (storage).

## R2 and R3

R2 (requery) and R3 (SQLCipher) load **the same sqlite-vec code** into a different SQLite. On the A32, R1 and R4
(two different SQLites) give the same speed, so the search loop decides the speed, not the loader. R3 also
decrypts every page it reads, so it can only be slower. **Proposed:** close EYKO-106 and EYKO-107 as
"not needed: same engine as R1 and R4". This needs the owner's yes on the board.

## Limits

- One phone for R1. The A32 was on the cable, and the room temperature was not written down.
- PSS leaves out the file cache. The memory test ran only one search per table.
- The A32 has this branch's app build installed (data kept); the kit build should be reinstalled after the card.
- The first full run stopped at 100k with `OutOfMemoryError` in **the test's own reference array** (a new
  205 MB array per size). It was fixed by allocating once; the log is kept as `proof/a32-2026-11-08-route-r1-logcat-run1-stopped-at-100k.txt`.
  Its 1k–50k numbers match the second run.

## Files

- CSVs: `docs/results/vectors/routes/a32-eyko105-route-r1-SM_A325F-20261108-1349.csv` (sweep),
  `…-r1-memory-SM_A325F-20261108-1352.csv` (three tables), `…-r1-SM_A325F-20261108-1347.csv` (the stopped first run),
  `a32-eyko108-r4-neon-…-1445.csv` and `a32-eyko108-r4-noneon-…-1447.csv` (R4 on the A32).
- Raw logcat: `docs/results/vectors/proof/a32-2026-11-08-route-r1-logcat.txt`, `…-route-r1-memory-logcat.txt`,
  `…-route-r1-logcat-run1-stopped-at-100k.txt`, `…-route-r4-logcat.txt`. Device readings: `…-route-r1-device.txt`, `…-route-r4-device.txt`.
- R4 libraries for the A32 run: `D:\eykon-cache\r4-a32\out\` (NEON `a9d93850…5288`, no-NEON `44a0ec39…1896`),
  built from Zara's `r4_jni.c` (b202f89) with `-O3 -DNDEBUG -DSQLITE_CORE -DSQLITE_ENABLE_FTS5 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_THREADSAFE=1`.
