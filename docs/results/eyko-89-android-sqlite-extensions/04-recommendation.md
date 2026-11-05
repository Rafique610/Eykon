# 4 · Recommendation

## Scoring the routes (from file 02)

Score 1 (poor) to 3 (good). Weights follow what this project values, in this order: it has to
work on both phones, it should be the simplest change (Ponytail), it has to keep laptop and
phone equal, and it should still be supported next year.

| Criterion (weight) | R1 bundled | R2 requery | R3 SQLCipher | R4 own NDK |
|---|---|---|---|---|
| Officially supported, maintained (3) | 3 | 1 | 3 | 1 |
| Effort to **test** on the phone (3) | 3 | 3 | 3 | 1 |
| Effort to **adopt** in the app (2) | 2 | 3 | 2 | 1 |
| Answers A3 convincingly (2) | 3 | 2 | 2 | 2 |
| Extra wins (FTS5, same SQLite everywhere) (1) | 3 | 3 | 3 | 2 |
| Extra risk (wrapper / supply chain / crypto / own JNI) (1) | 2 | 2 | 1 | 1 |
| **Weighted total (of 36)** | **33** | 27 | 30 | 15 |

R3 scores second, ahead of R2, because it is actively maintained. It still loses to R1: its
extension loading is a side effect rather than a documented API, and it brings encryption and
key management that no card asks for (see file 02).

## 1 · The bundled route for the lead to try first

**R1: androidx `BundledSQLiteDriver` + `addExtension`, with a sqlite-vec `.so` we build
ourselves.**

Why this one:
1. It is Google's documented, supported way to get a SQLite that loads extensions
   (`addExtension`, since androidx.sqlite 2.6.0). It is the strongest answer to A3.
2. It can be **tested without touching the app's Room setup**. Open the driver directly
   inside `VectorStorageSpikeTest`.
3. If it is adopted, it also brings FTS5 (`bm25()`), which closes the Head 6 gap, and SQLite
   3.53.4 on every phone instead of 3.32 to 3.50.

Why not R3 (second on score): it would make the database encrypted as a side effect, which
needs a password and key storage and costs CPU on every page read. Revisit it only if the
project decides it wants encryption at rest.

Why not R2 first, although it is cheaper to adopt: requery has not been pushed since
October 2025 and is served only from JitPack. That is a weak base for the project's storage
layer. **R2 stays the fallback** if the Room 2.8 + `getSupportWrapper()` migration proves
too heavy. requery works with Room 2.6.1 unchanged.

### Exact steps for the lead's test (card "Lead: sqlite-vec through a bundled SQLite on the phone")

1. Build `libvec0.so` for `arm64-v8a` (and `armeabi-v7a` if needed) from sqlite-vec v0.1.9
   source, using **NDK r28+** (or r27c with
   `-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384`) and
   `-DSQLITE_VEC_ENABLE_NEON`. Check `readelf -lW` shows `LOAD … 0x4000`.
   (The prebuilt also works on our two 4 KB phones, but it is 4 KB-aligned and scalar.
   Use it only for a first smoke test.)
2. Put it in `android/app/src/androidTest/jniLibs/arm64-v8a/` (test only). Add
   `androidTestImplementation("androidx.sqlite:sqlite-bundled:2.7.1")`. It needs Kotlin 2.0+,
   and we have 2.0.21.
3. In the test:
   `val drv = BundledSQLiteDriver().apply { addExtension(nativeLibDir + "/libvec0.so", "sqlite3_vec_init") }`,
   then `drv.open(path)`, `SELECT sqlite_version(), vec_version()`, create the `vec0` table,
   and run the same sweep as `blob_memory_fast`. Log the lines in the same proof format.
4. Pass marks, fixed before running:
   - It loads on **both** phones (that answers A3).
   - recall@20 = 1.0 against exact search (float32).
   - Report time, PSS and file size per size. **Adopt only if** it beats `blob_memory_fast`
     on memory at 50k with three tables **and** stays under 200 ms at 100k on the A32.
   - Optionally: `adb shell getconf PAGE_SIZE`, then repeat with 16 KB mode on the Pixel
     (developer option "Boot with 16KB page size") to show the self-built `.so` loads there.

## 2 · The fallback index to test on the laptop (EYKO-91)

**usearch (O4)**, `pip install usearch`, run through `uv run --with usearch`.

Why: it is the only candidate that is approximate (sub-linear), memory-maps an index from disk
(it addresses the heap wall, not just speed), supports i8 / f16, **and** ships official
Android arm64 builds with a Java binding. hnswlib is the simpler algorithm but has no Android
or Java build and no memory-mapped view. FAISS has no Android package.

EYKO-91 settings: metric `cos`, dtype f32 then i8, default `connectivity` / `expansion_add`.
If recall@20 < 0.95, add one tuned row with a higher `expansion_search`. Build time and index
size are reported separately from query time. Pass mark, from the card: recall@20 ≥ 0.95
**and** ≥ 5× faster than in-memory BLOB at 300k.

## 3 · What should happen before either of those

The 4 Nov numbers (file 03) show the heap fails before speed does. The cheapest fix needs no
SQLite change: **off-heap int8 / f16 vectors with the same exact brute force (O1)**. It belongs
on the lead's EYKO-100 track. I recommend raising it as a card, because it may make the
bundled-SQLite migration unnecessary for the app, though still worth testing for A3.

## Things noticed along the way (flagged, not acted on)

1. **16 KB pages affect the whole app, not just sqlite-vec.** The app already ships native
   code (`onnxruntime-android:1.18.0`, `litertlm-android:0.16.1`). Run `check_elf_alignment.sh` on the release
   APK. Google Play blocks non-16 KB updates from 1 Feb 2027 for targetSdk 35+. This is not
   checked here, so it should be its own card.
2. **NDK r27c on the laptop** does not build 16 KB-aligned by default. Any native build we
   add needs r28+ or the two linker flags.
3. **BundledSQLiteDriver connections are not thread-safe** (multi-thread mode). Our
   `VideoVectors` is `@Synchronized` and has one worker. Using the driver without Room needs
   `SQLITE_OPEN_FULLMUTEX` or a single connection.
4. **requery's version labels disagree:** the README shows 3.50.4, while the newest tag and
   JitPack build are 3.49.0. If R2 is used, pin the exact tag.
5. My earlier plan file (`docs/plans/head-2-research/01-…`) guessed SQLCipher would *not*
   allow extensions. Its source shows it does (`sqlite3_enable_load_extension(db, 1)` on every
   connection). The plan's table is corrected here.
