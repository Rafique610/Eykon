# Sources

Every source was read on **5 November 2026**. "Raw" means the file was fetched and searched
(`curl` + `grep` / `readelf`), with the output kept in [`evidence/`](evidence/).

| # | Title | Link | Used for |
|---|---|---|---|
| S1 | AOSP `external/sqlite` `dist/Android.bp` (main and android11/13/14/15/16-release) | https://android.googlesource.com/platform/external/sqlite/+/refs/heads/main/dist/Android.bp | `-DSQLITE_OMIT_LOAD_EXTENSION`, no FTS5 / RTREE, `OMIT_COMPILEOPTION_DIAGS` (raw) |
| S2 | AOSP `frameworks/base` `core/jni/android_database_SQLiteConnection.cpp` | https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/jni/android_database_SQLiteConnection.cpp | No extension call in the framework JNI (raw) |
| S3 | Android reference: `android.database.sqlite` package summary | https://developer.android.com/reference/android/database/sqlite/package-summary | SQLite version per API level; makers may ship other versions |
| S4 | Jetpack release notes: SQLite | https://developer.android.com/jetpack/androidx/releases/sqlite | `addExtension` in 2.6.0; minSdk 23; latest 2.7.1 / 2.8.0-alpha03; Kotlin needs |
| S5 | Android reference: `BundledSQLiteDriver` | https://developer.android.com/reference/kotlin/androidx/sqlite/driver/bundled/BundledSQLiteDriver | `addExtension(fileName, entryPoint)` contract; multi-thread mode |
| S6 | androidx `sqlite/sqlite-bundled/build.gradle` (androidx-main) | https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/sqlite/sqlite-bundled/build.gradle | Bundled SQLite 3.53.4 and its compile flags (raw) |
| S7 | Android KMP docs: SQLite | https://developer.android.com/kotlin/multiplatform/sqlite | BundledSQLiteDriver "recommended"; SupportSQLite → driver migration |
| S8 | Android KMP docs: Room (KMP migration) | https://developer.android.com/training/data-storage/room/room-kmp-migration | Compatibility mode without a driver; `getSupportWrapper()` |
| S9 | Jetpack release notes: Room | https://developer.android.com/jetpack/androidx/releases/room | `setDriver` in 2.7.0; `room-sqlite-wrapper` in 2.8.0; latest 2.8.5 |
| S10 | requery/sqlite-android README and sources | https://github.com/requery/sqlite-android | JitPack coordinates, API 21, Apache-2.0, sizes, `customExtensions`, `RequerySQLiteOpenHelperFactory`, FTS5 flags (raw) |
| S11 | GitHub API: requery/sqlite-android repo + tags; JitPack latestOk | https://api.github.com/repos/requery/sqlite-android | Last push 14 Oct 2025; newest tag 3.49.0 |
| S12 | sqlcipher/sqlcipher-android README, `Android.mk`, `android_database_SQLiteConnection.cpp`, LICENSE | https://github.com/sqlcipher/sqlcipher-android | Extension loading enabled per connection; Room 2 / 3; BSD-style licence (raw) |
| S13 | sqlite-vec releases (GitHub API) | https://github.com/asg017/sqlite-vec/releases | v0.1.9 Android assets and sizes |
| S14 | sqlite-vec docs: Android and iOS | https://alexgarcia.xyz/sqlite-vec/android-ios.html | Prebuilt loadables since v0.1.2; `.aar` planned |
| S15 | sqlite-vec issue #68 "Tracking issue: Android Support" | https://github.com/asg017/sqlite-vec/issues/68 | `addExtension("vec0.so","sqlite3_vec_init")` used with BundledSQLiteDriver; `lib<name>.so` naming |
| S16 | sqlite-vec PR #254 "Support android 16kb pages" (open) | https://github.com/asg017/sqlite-vec/pull/254 | Prebuilts 4 KB-aligned up to v0.1.10-alpha.4 |
| S17 | sqlite-vec PR #339 "Use NEON on Linux arm64" (open) and `Makefile` | https://github.com/asg017/sqlite-vec/pull/339 | No NEON on Android cross-builds; 3–5× NEON speedup claim (raw Makefile) |
| S18 | Android developers: Support 16 KB page sizes | https://developer.android.com/guide/practices/page-sizes | Play deadline 1 Feb 2027; alignment check; NDK r28 default; Pixel 16 KB developer option |
| S19 | `readelf -lW` on downloaded `vec0.so` (v0.1.9 aarch64) and `libusearch_c.so` (v2.26.6 arm64) | [evidence/prebuilt-so-alignment.txt](evidence/prebuilt-so-alignment.txt) | Both `LOAD` segments `0x1000` = 4 KB (own measurement) |
| S20 | unum-cloud/usearch README; Java README; release v2.26.6 assets | https://github.com/unum-cloud/usearch | HNSW, quantisations, view from disk, exact mode, Android zip, Java fat JAR, Apache-2.0 |
| S21 | nmslib/hnswlib (GitHub API) | https://github.com/nmslib/hnswlib | Apache-2.0, active (Sep 2026); header-only, no Android build found |
| S22 | FAISS `INSTALL.md` | https://github.com/facebookresearch/faiss/blob/main/INSTALL.md | No Android package; BLAS + OpenMP needed |
| S23 | ObjectBox docs: on-device vector search; FAQ | https://docs.objectbox.io/on-device-vector-search | HNSW approximate; +2.3 MB per ABI; core licence **not found** |
| S24 | Eykon repo: `docs/results/vectors/proof/*-2026-11-04-extensions-logcat.txt`, `*-2026-11-04-sweep-real.csv`, `*-2026-11-04-memory.csv` | (this repo, `feature/video-memory` @ 972091d) | Phone errors, fast-loop timings, all-table OOM |
| S25 | Eykon repo: `android/app/build.gradle.kts`, `android/build.gradle.kts` | (this repo) | Room 2.6.1, minSdk 31, targetSdk 35, AGP 8.5.2, Kotlin 2.0.21 |

## Looked for and not found

- An official sqlite-vec `.aar` or Maven package for Android: **not found** (issue #102 open).
- The APK size added by `sqlite-bundled`: **not found** in Google's docs.
- ObjectBox native core licence: **not found** in the docs read.
- An official FAISS Android build: **not found**.
- Whether `SupportOpenHelperFactory` (SQLCipher) accepts an empty password, which would mean
  extensions without encryption: **not checked**.
