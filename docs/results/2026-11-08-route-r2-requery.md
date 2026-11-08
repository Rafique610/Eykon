# Route R2: sqlite-vec through requery's SQLite, on the A32 (EYKO-106)

**Date:** 8 November 2026 · **By:** Rafique · **Card:** EYKO-106 · **Phone:** Samsung A32 · **Asked for by:** the lead (Taha), after R1 · **Supervisor questions:** A3, A5, B7

**Verdict: works, not adopted.** requery's SQLite (sqlite-android 3.49.0) loads our own sqlite-vec build on the
A32. It returns exactly the same top 20 as today's search at every size, and keeps three tables at 100k
rows at about 60 MB. It is also the cheapest route to adopt: it needs only androidx.sqlite 2.4.0, the same
version our Room 2.6.1 already uses. As first measured it took **486 ms at 100k**, 2.1× R1 (230 ms) on
the same phone.

**Why it was slower (measured, section "Why R2 was 2× slower"):** requery's engine is not slower. requery
creates every new database with **1 KB pages**, because its `SQLiteGlobal.getDefaultPageSize()` returns a
hard-coded 1024. Google's SQLite uses 4 KB. On the **same file**, both engines run at the same speed
(4 KB file: Google 235.8 ms, requery 233.8 ms; 1 KB file: Google 485.0 ms, requery 485.1 ms). One line,
`PRAGMA page_size = 4096` before the first table, gives R2 R1's speed. **Even then it is 2.5× slower than
today's in-memory search (93 ms)**, so by the marks written before the run (memory **and** speed within
10 %) it fails on speed.

**Correction history, all on 8 Nov:**
1. R1's write-up said the route only changes the loader, so speed would match.
2. R2's first result (486 ms) looked like that was wrong.
3. The diagnosis shows the loader and engine really do not matter here; requery's default page size does.

## What was tested

- **Route:** `com.github.requery:sqlite-android:3.49.0` from JitPack. JitPack is limited to the group `com.github.requery`
  in `android/settings.gradle.kts`, so nothing else can be fetched from it. The database is opened with
  `io.requery.android.database.sqlite.SQLiteDatabase.openDatabase(config)`, after
  `config.customExtensions.add(SQLiteCustomExtension(<path>/libvec0.so, "sqlite3_vec_init"))`.
  Test: `android/app/src/androidTest/java/com/eykon/memory/spike/RouteR2Test.kt`.
- **Plugin, data, queries, reference and CSV format:** the same as R1 (EYKO-105). Our EYKO-104 build loaded
  from the test assets (SHA256 logged: NEON `264ec326…3e46`, no-NEON `ccd7178d…8329`), real own-clip vectors
  plus noise, 1 warm-up + 20 queries × 5 runs, top 20, `vec0` with the default L2 metric. The reference is
  `blob_memory_fast`, timed in the same run.
- **Phone:** Samsung A32, Android 13, on USB, battery 100 %, battery temperature 27.1 → 27.7 °C
  (`proof/a32-2026-11-08-route-r2-device.txt`). The CSVs say `2cb5b26+r2test-uncommitted`; the code that ran
  is the code in the commit that adds this file.

## Load check (claims C1, C3)

From `proof/a32-2026-11-08-route-r2-logcat.txt`:

- `R2 loads: sqlite 3.49.0, vec_version v0.1.9, first open with plugin 105.1 ms` (R1: 10.2 ms)
- `R2 vec_debug: … Commit: e9f598abfa0c06b328d8fe5da9c3760cce74be10 | Build flags:  neon`
- `R2 fts5 works: bm25 = -1e-06`

## Speed: median ms of the 5 run medians (slowest p95 of the 5 runs in brackets), same A32

| Rows | R2 requery (NEON) | R1 Google (NEON) | Today: `blob_memory_fast` (this run) | R2 against today |
|---|---|---|---|---|
| 1,000 | 6.8 (7.9) | 3.3 (4.1) | 1.2 (1.4) | 5.6× slower |
| 5,000 | 27.2 (28.8) | 13.2 (19.1) | 5.0 (5.1) | 5.5× |
| 20,000 | 104.5 (138.8) | 53.0 (101.7) | 20.4 (22.8) | 5.1× |
| 50,000 | 239.7 (249.6) | 88.8 (126.8) | 46.2 (47.4) | 5.2× |
| 100,000 | **485.8** (554.4) | **230.2** (233.6) | **93.2** (94.5) | **5.2×** |

- **Recall@20 = 1.0000 (400 of 400) at every size.**
- **No NEON:** 107.9 ms at 20k and 524.9 ms at 100k. NEON gains only 3–8 % here, against 11–17 % on R1, because
  most of R2's time goes into reading pages, not into the distance loop (next section).
- **The gap is in the scan, not the call:** R2 is 2.1× R1 at 1k and still 2.1× at 100k. A fixed cost per query
  (the cursor, the binding) would fade as the table grows; this does not.
- **Insert time into `vec0`** (one table): 20k 10.7 s, 100k 49.2 s (R1: 9.1 s and 32.5 s).
- **These R2 numbers are for requery's default 1 KB pages.** With 4 KB pages it searches at R1's speed (next section).

## Why R2 was 2× slower: requery's default page size

**Test** (`RouteR2DiagnoseTest`, A32, 100k rows, median of 3 runs × 20 queries,
`proof/a32-2026-11-08-route-r2-diagnose-logcat.txt`): two files were written, one by each engine. Both engines then
searched **both** files, after logging 12 runtime settings (`PRAGMA page_size, cache_size, mmap_size, journal_mode, …`).
Last, requery searched again with every setting that differs set to Google's value.

| File | Its page size | Google searches it | requery searches it | requery with Google's settings |
|---|---|---|---|---|
| written by Google | 4,096 B | 235.8 ms | **233.8 ms** | 233.0 ms |
| written by requery | 1,024 B | **485.0 ms** | 485.1 ms | 482.1 ms |

- **The engine does not matter; the file does.** On the same file the two engines are within 1 %.
- **The only setting that differs between the two files is `page_size`** (4,096 against 1,024). `cache_size` (−2000, about 2 MB),
  `mmap_size` (0), `temp_store`, `cache_spill`, `auto_vacuum` and `synchronous` are the same. The two connection settings
  that do differ, `journal_mode` (delete / truncate) and `soft_heap_limit` (0 / 8 MB), make no difference when matched (last column).
- **Where 1 KB comes from:** requery 3.49.0's `SQLiteGlobal.getDefaultPageSize()` reads the storage block size and then
  returns a hard-coded `1024`. Its `SQLiteConnection.setPageSize()` runs `PRAGMA page_size=1024` on every new
  connection. That only takes effect on a database that has no tables yet, which is why Google's 4 KB file stayed at 4 KB
  when requery opened it. Source: `github.com/requery/sqlite-android`, tag 3.49.0, `SQLiteGlobal.java` lines 66–72, `SQLiteConnection.java` lines 286–293.
- **Why page size matters to vec0 (likely mechanism, not separately measured):** sqlite-vec keeps vectors in chunk
  BLOBs (by default 1,024 vectors × 2,048 B = 2 MB each). SQLite stores a BLOB that big as a chain of overflow pages, and a
  search reads every chunk. With 1 KB pages a 2 MB chunk is about 2,000 pages; with 4 KB pages about 500. The search does
  4× more page reads and copies per chunk, and the measured cost is 2.1×. Compile flags were checked and ruled out: both
  are optimised (requery `-O3`; Google's Android build `-Oz`, which is the faster one here).
- **Fix if R2 were ever used:** run `PRAGMA page_size = 4096` (or 16384) on a new database before its first table. An existing
  1 KB database needs `VACUUM` after the PRAGMA. The app's current database was made by Android's own SQLite, which uses 4 KB.

## Memory: three tables, n rows each, one search per table

| Rows each | R2 total PSS before → after | Java heap | Tables searched | Today (BLOBs in Java memory) |
|---|---|---|---|---|
| 20,000 | 56 → 58 MB | 3 MB | 3 of 3 | fits |
| 50,000 | 56 → 60 MB | 3 MB | 3 of 3 | **out of memory** |
| 100,000 | 56 → 60 MB | 3 MB | 3 of 3 | **out of memory** |

As with R1, the vectors stay in the file and PSS leaves out the file cache.

## Size and 16 KB

- requery's own library `libsqlite3x.so` (arm64) is **1,836,232 B**. With our `libvec0.so` (145,936 B) that is
  about **1.98 MB** for 64-bit phones (the research said about 1.7 MB). The package also ships armeabi-v7a,
  x86 and x86_64 copies (1.2–1.9 MB each) unless `abiFilters` is set.
- `readelf -lW libsqlite3x.so`: every LOAD aligned **`0x4000`** (16 KB). `zipalign -c -P 16 -v 4` on the test APK: **Verification successful**.

## Claims from the research

| Claim | Result | Evidence |
|---|---|---|
| C1: loads sqlite-vec on the phone | **True** (A32) | load lines above |
| C2: cheapest to adopt, Room 2.6.1 and one builder line | **Supported, not run.** requery's POM needs only `androidx.sqlite:sqlite:2.4.0` and `androidx.core:core:1.15.0`, so unlike R1 it forces no androidx.sqlite jump. The one-line switch of the app's Room builder (card step 6) was **not run**: it would open the phone's real app database through requery, and the speed result already rules R2 out | POM: `jitpack.io/com/github/requery/sqlite-android/3.49.0/…pom` |
| C3: brings FTS5 | **True** | `R2 fts5 works` |
| C4: about 1.7 MB arm64 | **About 1.98 MB** with our plugin (1.84 MB for requery alone) | APK listing |
| Risk: maintenance and supply chain | Stands: one project, tag 3.49.0 (README says 3.50.4), served by JitPack | EYKO-89 |

## Against the pass marks (written 8 Nov, before the run)

- **Works:** yes. It loads, `vec_version` = v0.1.9, and recall@20 = 1.0 at every size.
- **Worth keeping** needed **both** marks: (a) three tables at 50k without running out of memory **passes**; (b) no more than 10 % slower
  than `blob_memory_fast` at 100k **fails**: 486 against 93 ms with requery's default, and still 234 against 93 ms (+151 %) with 4 KB pages.
- **Verdict: works, not adopted.** It is the cheapest to adopt (no androidx.sqlite jump), but even with the page-size fix
  it is as slow as R1, 2.5× today's in-memory search.

## What this changes

- **The loader and engine do not set the speed; the database's page size does.** All three sqlite-vec routes measured on the
  A32 (R1, R2 with 4 KB pages, R4) land at 230–234 ms at 100k.
- **R3 (SQLCipher, EYKO-107): dropped** by the owner on 8 Nov, with the lead's agreement. SQLCipher would run the same
  search, also decrypt every page it reads, and no card asks for encryption. If it is ever revisited, check its page size first.
- **EYKO-98:** every sqlite-vec route is about 2.5× slower than today's in-memory search on the A32. The memory fix without that
  cost is still EYKO-109's mapped file.
- **For any future SQLite work:** record `PRAGMA page_size` with every timing. It can halve the speed of large BLOB reads.

## Limits

- One phone (A32), on USB. Pixel (EYKO-83 storage) and Infinix not run.
- Step 6 (switching the app's Room builder) not run, for the reason in C2.
- The full R2 sweep (1k–100k, 5 runs) ran with requery's default 1 KB pages. The 4 KB result is from the diagnosis
  (100k only, 3 runs × 20 queries), not a full rerun.
- How 1 KB pages cost 2× (overflow-page chain reads) is the likely mechanism, not separately measured.

## Files

- CSVs: `docs/results/vectors/routes/a32-eyko106-route-r2-SM_A325F-20261108-1528.csv` (sweep), `…-r2-memory-SM_A325F-20261108-1533.csv`.
- Raw logcat: `docs/results/vectors/proof/a32-2026-11-08-route-r2-logcat.txt`, `…-route-r2-memory-logcat.txt`,
  `…-route-r2-diagnose-logcat.txt` (the page-size test); device readings `…-route-r2-device.txt`; screenshot `…-route-r2-logcat.png`.
- Tests: `RouteR2Test.kt` (sweep, memory), `RouteR2DiagnoseTest.kt` (same files, both engines).
