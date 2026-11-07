# Route R4: our own NDK build of SQLite with sqlite-vec compiled in (EYKO-108)

Run by Zara Tahir on her Infinix X670 only, 8 November 2026 (build and runs 00:55 to 02:35 phone and laptop clock).
Answers supervisor questions A3 ("can an app ship its own SQLite?") and B7 for this route. **One phone out of the
two the card asks for: the A32 and the Pixel were not run.** The card's pass marks say the lead confirms them before the
run; that was not obtained, so the verdicts use the marks as written, on one phone.

## What was built

- `android/app/src/androidTest/cpp/`: `CMakeLists.txt` and `r4_jni.c` (88 lines of C). SQLite amalgamation **3.53.4**
  (SHA256 `1e71ddf9...e87d`) and sqlite-vec **0.1.9** (SHA256 `b87cdda1...a8c9`), compiled into one `.so` with the Android
  NDK **r28c (28.2.13676358)**, flags `-O3 -DSQLITE_CORE -DSQLITE_ENABLE_FTS5 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_THREADSAFE=1`
  and, for the NEON build, `-DSQLITE_VEC_ENABLE_NEON`. A second build without NEON. The sources are **not committed**:
  `fetch.ps1` downloads them and checks the SHA256; `build.ps1` builds both libraries for arm64-v8a and copies them to
  `androidTest/jniLibs/`, so they are in the test APK only.
- sqlite-vec is registered for every connection with `sqlite3_auto_extension(sqlite3_vec_init)` in `JNI_OnLoad`. Nothing is
  loaded at run time: no `load_extension`, no second file.
- `NativeSqlite.kt` (41 lines): open, exec, prepare, step, bind and read int / double / blob / text, close.
  `RouteR4StaticTest.kt` (214 lines): versions, the sweep, the three-table memory test.
- The phone's own SQLite stays 3.32.2; this test opens its own 3.53.4 copy through the JNI layer, not through Room.

## Loads (C1, A3)

On the Infinix (raw: `proof/infinix-2026-11-08-route-r4-versions-logcat.txt`, tag `EYKO31`):
`sqlite_version() = 3.53.4`, `vec_version() = v0.1.9`, `CREATE VIRTUAL TABLE ... USING fts5(x)` ok,
`CREATE VIRTUAL TABLE ... USING vec0(embedding float[4])` ok, a vec0 insert and select returned the row.
Opening the first connection took 0.2 to 0.9 ms. **C1 holds on this phone**: it worked the first time it ran on the device.

## Library checks (step 3), raw in `proof/route-r4-readelf-2026-11-08.txt`

- 16 KB pages: every `LOAD` segment of both libraries has alignment `0x4000`. `zipalign -c -P 16 -v 4` on the test APK:
  both `.so` files `OK`, "Verification successful". No extra linker flags were needed with NDK r28c.
- Exported JNI functions: all 16 `Java_com_eykon_memory_spike_NativeSqlite_*` and `JNI_OnLoad` are present.
- SHA256: `eykon_r4.so` `449b8952...c61a`, `eykon_r4_noneon.so` `94818178...4b65`.
- Size: the libraries as built are 9.4 MB each (not stripped). Stripped with `llvm-strip --strip-unneeded`: 1.71 MB
  (NEON) and 1.71 MB (no NEON), about 0.85 MB compressed. **APK size added for one stripped library is about 0.85 MB**
  (estimate from `strip` and zlib, not from APK Analyzer; the test APK holds the unstripped libraries stored uncompressed).

## Speed and answers (image table, 512 numbers, real vectors, 1 warm-up + 20 queries x 5 runs, top 20)

Median of the 5 run medians, ms. Recall@20 against exact search (the exact top 20 by dot product, computed in the same pass
over the vector stream) was **1.0000 (400 of 400) at every size, both builds**. DB file size is the vec0 database.

| Rows | sqlite-vec, NEON | sqlite-vec, no NEON | NEON speed-up | DB file | Worst p95 (NEON) |
|---|---|---|---|---|---|
| 1,000 | 2.4 | | | 2.2 MB | 4.4 |
| 5,000 | 7.0 | | | 10.6 MB | 7.5 |
| 20,000 | 24.6 | 31.5 | 1.3x | 42.5 MB | 25.8 |
| 50,000 | 58.0 | | | 104.1 MB | 60.9 |
| 100,000 | 110.3 | 152.3 | 1.4x | 208.2 MB | 114.8 |

The five runs agree closely (100,000 rows: 109.7 to 112.4 ms). Insert time into vec0 at 100,000 rows: 31 s (1 table).

For comparison, the in-memory loops on the same phone from the 7 Nov cool run (EYKO-95; random vectors, top-20 only, so
only roughly comparable): fast loop 3.6 / 13.9 / 34.4 / 69.1 ms at 5k / 20k / 50k / 100k. sqlite-vec is **1.6 to 1.9 times slower**
than that loop (110.3 against 69.1 at 100,000). The app's own search (`VideoVectors.scores`, EYKO-109 table, all rows
scored) took 296.8 ms at 100,000 rows, so against the app's loop sqlite-vec is faster; the two are not the same operation
(the app needs every frame's score, vec0 returns the top k).

## Memory with all three tables (image 512, text 384, audio-sized 512), n rows each

Total PSS before / after (MB), native heap after 8 MB, Java heap after 3 MB, tables built 3 of 3 at **every size up to 100,000**
(`eyko108-r4-memory-neon` CSV): 5k 58 / 56; 20k 56 / 56; 50k 56 / 56; 100k 56 / 56. **No out-of-memory at any size.**

Careful with this number: PSS stays flat because the vectors stay in the database file and the OS caches the file pages,
which `Debug.getMemoryInfo` does not count as the app's. The data still uses RAM as page cache, which the system can drop. It was **not**
measured how much RAM that takes or what the search costs when those pages are dropped (the EYKO-109 background test
showed a 3.8 times slower first search for the mapped file; nothing like it was run for vec0).

## Claims (C1 to C3)

- **C1, it always works because nothing is loaded at run time: holds on the Infinix** (one phone, Android 13).
- **C2, it is the most effort: about 2 hours of my time for this test, most of it waiting on the NDK and downloads (r26d then r28c,
  about 1.5 GB), 399 lines written** (88 C, 23 CMake, 33 PowerShell scripts, 41 + 214 Kotlin). This is the test only: a production
  version needs a JNI database layer replacing Room's use of SQLite (open, transactions, prepared statements, migrations, threads)
  and our own native build in the app, which this test does not include. Not weighed against R1 to R3 (that is EYKO-98).
- **C3, full control (NEON on, 16 KB pages, only the flags we need): holds.** NEON gives 1.3 to 1.4 times faster search;
  16 KB alignment came out right on r28c with no flags; FTS5 is on and `SQLITE_OMIT_LOAD_EXTENSION` stays on.

## Against the card's pass marks (one phone only)

- **Loads: yes on the Infinix.** A32 and Pixel not run, so A3 is answered for this route on one phone only.
- **Correct: yes**, recall@20 = 1.0000 at 1k, 5k, 20k, 50k and 100k.
- **Worth adopting only if (a) or (b), and nothing past the 200 ms target:** (a) three tables at 50k no longer run out of memory:
  **met** (all three tables build at 100,000 rows with a flat 56 MB PSS; today's array fails at 50,000). (b) faster than
  `blob_memory_fast` at 100k on the A32: **not met on the Infinix** (110 against 69 ms); the A32 was not run. 110 ms at 100,000 rows is under the 200 ms target
  (our own target, no source yet, EYKO-101).
- **Verdict (one phone): works, exact, memory problem solved at 100k rows, but 1.6 to 1.9 times slower than the fast in-memory loop, and the effort
  (own native build and JNI layer) is not proven small.** Whether it beats R1 to R3 and the memory-mapped float32 file from EYKO-109 is the lead's
  decision (EYKO-98).

## Not tested / limits

- A32 and Pixel not run; the card's `Samsung A32` comparison for mark (b) is missing.
- Not exercised through Room, through the app's whole search (which needs every frame's score, not only the top 20), or
  with the 2,400-hit check. vec0 returns the nearest k rows; the app's time-window growth needs all scores, so this is not a drop-in for `VideoVectors.scores`.
- The phone was plugged in during these runs and not in flight mode (not a thermal or protocol-controlled run).
- The APK size is an estimate; APK Analyzer was not run. The app APK was not rebuilt with the library inside.
- The no-NEON build was run at 20k and 100k only, as the card says.

## Evidence files

`docs/results/vectors/route-r4/infinix-2026-11-08-eyko108-r4-neon-*.csv`, `...-r4-noneon-*.csv`, `...-r4-memory-neon-*.csv` (pulled unedited
from the phone), `docs/results/vectors/proof/infinix-2026-11-08-route-r4-logcat.txt` and `...-route-r4-versions-logcat.txt` (raw logcat),
`route-r4-readelf-2026-11-08.txt`, `route-r4-build-log-2026-11-08.txt`. Code: `android/app/src/androidTest/cpp/`, `NativeSqlite.kt`, `RouteR4StaticTest.kt`.
