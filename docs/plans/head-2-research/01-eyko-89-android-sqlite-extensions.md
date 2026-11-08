# EYKO-89 · Why Android blocks SQLite extensions, and every way around it

Card: [EYKO-89](https://synverk.abdulhaque.dev/projects/bc6e8969-e244-4916-b158-2903baf02996/tasks/89).
Answers supervisor questions A2, A3 and B7. Branch: `taha/eyko-89-android-sqlite-extensions`
from `origin/feature/video-memory`.
Deliverable: `docs/results/<date>-android-sqlite-extensions.md`, with a sources table (title,
link, date read). Every claim needs a source or the words "not found".

> This file is the **approach**. Anything marked *(verify)* below is what I expect to find,
> written from memory. It must be confirmed against the live source before it goes into the
> deliverable.

## The problem in one paragraph

Room 2.6.1 uses `android.database.sqlite`, which is the SQLite the OS ships. Both phones gave
`no such module: vec0` and `no such function: load_extension`. The error message alone
cannot tell an examiner whether the failure comes from sqlite-vec or from Android. The
evidence suggests Android: two phones with different Android versions (13 and 17) and
different SQLite versions (3.32.2 and 3.50.6) give identical errors, so the cause is a
platform policy, not a version bug. The card asks for that claim to be proven from Android
source and for a list of real ways around it.

## Step 1 · Prove it is Android (A2)

Where to look, in order:

1. **AOSP `external/sqlite`**: the build file (`dist/Android.bp`) and its `cflags`. I expect
   `-DSQLITE_OMIT_LOAD_EXTENSION` *(verify)*. Quote the line, link it on
   `cs.android.com` / `android.googlesource.com` with the branch tag (for example
   `android13-release` and the latest), and record which Android versions it covers.
2. **The `android.database.sqlite` API reference.** `SQLiteDatabase` has no
   `enableLoadExtension` or `loadExtension` method. Contrast this with desktop Python
   (`sqlite3.Connection.enable_load_extension`) and with the requery API.
3. **The `vec0` half of the error.** This is not a bug. A virtual-table module exists only
   once something registers it, and sqlite-vec is an external extension that no OS SQLite
   includes. Source: the sqlite-vec README on how to load it.
4. **The SQLite version on each Android release.** The `android.database.sqlite` package
   docs list a SQLite version per API level. Cite them next to the two proof logs to show
   that "newer Android" does not help.

Write the answer so it splits the two errors cleanly:

- `load_extension` is missing because Android compiles it out. That part is the Android
  problem.
- `vec0` is missing because nothing registered the module. That would be true of any SQLite
  that lacks the extension.

## Step 2 · Routes that do allow extensions (A3)

For each route, fill in: how it works, minimum Android / Room version, licence, APK size
added, whether it is maintained (last release date), and a known app or sample that uses it.

| # | Route | How sqlite-vec gets in | Expected facts *(verify every cell)* | Fit for Eykon |
|---|---|---|---|---|
| R1 | **androidx `sqlite-bundled`** (`BundledSQLiteDriver`) | Room 2.7+ takes the driver through `setDriver(BundledSQLiteDriver())`. The driver ships its own SQLite compiled with extension loading. Look for an `addExtension(fileName, entryPoint)` API added in a 2.5.x / 2.6.x release *(verify the exact version)*. sqlite-vec's `.so` for arm64-v8a goes in `jniLibs`. | Apache-2.0, Google-maintained, about 1–1.5 MB per ABI *(measure)*. Room needs a 2.6.1 → 2.7+ upgrade, which brings KMP-style APIs, and `SupportSQLiteDatabase` code paths may change. | **Best first try.** Official, maintained, and Room stays. |
| R2 | **requery `sqlite-android`** | A drop-in copy of `android.database.sqlite` with its own SQLite. `SQLiteDatabaseConfiguration.customExtensions` / `SQLiteCustomExtension` load a `.so` by entry point. Plugs into Room through `RequerySQLiteOpenHelperFactory`. | Apache-2.0, published on JitPack / Maven *(verify coordinates)*, adds about 1–2 MB per ABI. Maintenance has slowed: check the last release date. | Good fallback. No Room upgrade needed, but it is a third-party fork. |
| R3 | **SQLCipher for Android** (`net.zetetic:sqlcipher-android`) | Its own SQLite build with encryption. Extension loading is likely compiled out or undocumented *(verify)*. | BSD-style, maintained, larger (+crypto). | Probably not. Note it as "checked, does not give extensions" if that is what the source says. |
| R4 | **Own NDK build**: SQLite amalgamation + `sqlite-vec.c` statically linked, registered with `sqlite3_auto_extension(sqlite3_vec_init)` | No `load_extension` at all. The module is compiled in. A JNI wrapper, or a custom `SupportSQLiteOpenHelper` around it. | Public domain + MIT/Apache (sqlite-vec). Smallest runtime surface, but we would own the build and the JNI. | Most robust, highest effort. Keep it as plan C. |
| R5 | **A published sqlite-vec Android build** | Check sqlite-vec GitHub **releases** for `android-aarch64` / `android-x86_64` loadable assets, and its **issues** for "android". I believe loadable Android builds have appeared in the releases *(verify version and file names)*. | Decides whether R1/R2 need our own NDK build of the `.so` or can download one. | An input to R1/R2, not a route on its own. |

For each route, also note whether **`text_vec` / FTS4 changes**. A bundled SQLite usually
ships **FTS5**. That would also close the Head 6 limitation ("phone has FTS4, no `bm25()`"),
which `core.md` says must eventually match the laptop. This side benefit is worth stating in
the recommendation.

## Step 3 · What if brute force gets too slow (B7)

The 3 Nov sweep says this is not hypothetical: 200 ms is crossed at about 41k vectors on the
A32 and about 78k on the Pixel, and the Pixel ran out of memory at 300k (see
[00-context](00-context.md)).

| Option | Exact / approximate | Licence | Android support | Size / memory | Notes |
|---|---|---|---|---|---|
| sqlite-vec float32 (`vec0`) | Exact (brute force) | MIT / Apache-2.0 | Through R1/R2/R4 | File half of BLOB (42.5 vs 82.1 MB at 20k, laptop) | Still linear. It moves the loop into C/SIMD and out of the Java heap. |
| sqlite-vec int8 / bit | Exact **over quantised vectors**, so recall can be < 1 | same | same | 4× / 32× smaller | Bit quantisation + float rerank is a known pattern *(cite sqlite-vec docs)*. |
| **usearch** | Approximate (HNSW), optional exact | Apache-2.0 | Official Java/JNI binding. Check for a prebuilt Android AAR *(verify)* | Small native lib, f16/i8 storage | Single header, can memory-map the index from disk, so it stays off the heap. Strong candidate. |
| hnswlib | Approximate (HNSW) | Apache-2.0 | No official Android build. Header-only C++, so NDK + JNI by hand | Index ≈ vectors + graph links | Simplest algorithm to reason about. Fine as the laptop reference. |
| FAISS | Exact and approximate (Flat, IVF, HNSW, PQ) | MIT | No official Android package. Community NDK builds exist *(verify)* | Large lib | Overkill for under 1M vectors. Hard to ship. |
| ObjectBox vector search | Approximate (HNSW) | Bindings Apache-2.0, core closed binary *(verify)* | First-class Android | Its own DB, not SQLite | Would replace SQLite storage, which conflicts with the raw-SQL decision. |
| **No new library**: int8/f16 off-heap + top-k heap + ONNX Runtime `MatMul`+`TopK` | Exact (int8: near-exact) | — | ONNX Runtime 1.18 already in the app | 4× less memory with int8 | Not on the card's list, but cheapest to ship. Belongs to EYKO-100 (lead). Mention it as the "before an index" step. |

## Step 4 · Recommendation (the shape of the answer)

- **Route for the lead to try first (feeds the card "Lead: sqlite-vec through a bundled
  SQLite on the phone"): R1, `BundledSQLiteDriver` + sqlite-vec arm64 `.so`.** It is
  official and maintained, keeps Room, brings FTS5 as a bonus, and gives the cleanest answer
  to A3 ("yes, we tried Android's own supported way"). If the extension API is missing or the
  Room 2.7 upgrade breaks too much, fall back to R2 (requery), which needs no Room upgrade.
- **Fallback index to test on the laptop (EYKO-91): usearch.** It has an official Java
  binding, supports int8/f16, and can memory-map an index from disk, which addresses the
  heap OOM as well as speed. Its Python package is pip-installable, so laptop recall and speed
  can be measured the same day.

## Alternatives for running the card itself

| Approach | Effort | Strength | Risk |
|---|---|---|---|
| **A. Desk research only** (as the card asks) | ~1 day | Fastest, and it fits "research" | Claims about APIs could still be wrong in practice |
| **B. Desk research + a 30-minute proof** (recommended) | +½ day | Add `androidx.sqlite:sqlite-bundled` to a scratch Android project, open a connection, run `select sqlite_version()` and `select load_extension(...)` or `addExtension`. A logcat line turns a cited claim into a demonstrated one. | Stays inside "research" only if it is kept in a scratch project, not in the app (the app change is the lead's card) |
| C. Full port on a branch | 2–3 days | Answers A3 completely | Overlaps the lead's card. Do not do it here. |

## Done-when checklist

- [ ] The AOSP line is quoted, linked, and tied to the Android versions it applies to (A2)
- [ ] R1–R5 table filled in, with every cell sourced or marked "not found" (A3)
- [ ] B7 table filled in with Android support checked per option
- [ ] One route named for the lead, one index named for EYKO-91
- [ ] Sources table: title, link, date read
- [ ] PR to `feature/video-memory`, card moved to Review, check output pasted as a comment
