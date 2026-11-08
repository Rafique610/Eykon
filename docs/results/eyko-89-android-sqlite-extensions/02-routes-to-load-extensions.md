# 2 · Every way to load sqlite-vec on Android (supervisor question A3)

> **Android apps can ship their own SQLite. Did you try that route?**
> Not yet on a phone. That test is the lead's card. This file lists every route, sourced, and
> picks the one to try first ([04-recommendation.md](04-recommendation.md)).

The idea behind every route: Android's own SQLite cannot load extensions (file 01), so the app
**brings its own SQLite build**, compiled without `SQLITE_OMIT_LOAD_EXTENSION`, and loads
sqlite-vec into that.

## Where Eykon starts from

These facts decide how much each route costs. They come from the repo,
`android/app/build.gradle.kts` and `android/build.gradle.kts`:

| | Today |
|---|---|
| Room | 2.6.1, platform SQLite through `SupportSQLiteOpenHelper` |
| How video code talks to SQLite | Raw SQL on `SupportSQLiteDatabase` (`VideoVectors.kt`, `VideoSearch.kt`, …) |
| minSdk / targetSdk | 31 / 35 |
| AGP / Kotlin | 8.5.2 / 2.0.21 |
| NDK on the laptop | r27c (it does **not** build 16 KB-aligned by default; r28+ does) |
| ABIs shipped | No `abiFilters`, so whatever the dependencies ship |

---

## R1 · androidx `sqlite-bundled` (`BundledSQLiteDriver.addExtension`)

**How it works.** Google's own SQLite build, shipped as a native library inside the
`androidx.sqlite:sqlite-bundled` artifact. Since **2.6.0 (10 Sep 2025)**,
`BundledSQLiteDriver` has `addExtension(fileName, entryPoint)`. It "registers a
dynamically-linked SQLite extension to load for every subsequent connection opened with this
driver". For sqlite-vec that is `addExtension("<path>/libvec0.so", "sqlite3_vec_init")`. A
user in the sqlite-vec Android tracking issue (#68) reports exactly this call.

| Fact | Value | Source |
|---|---|---|
| Latest stable | 2.7.1 (9 Sep 2026); 2.8.0-alpha03 (21 Oct 2026) | androidx sqlite release notes |
| SQLite version bundled | 3.53.4 (`sqliteVersion.set("3.53.4")`) | `sqlite-bundled/build.gradle`, androidx-main |
| Extension loading compiled in | Yes: no `SQLITE_OMIT_LOAD_EXTENSION` among its 21 flags | same file ([evidence](evidence/replacement-sqlite-build-flags.txt)) |
| FTS5 / RTREE / JSON1 | All enabled | same file |
| Min Android | API 23 since 2.6.0 (we are on 31) | release notes |
| Kotlin | Compiled with Kotlin 2.0 since 2.5.0-alpha13. 2.8.0-alpha03 needs Kotlin 2.2 | release notes |
| Room needed | `setDriver()` from **Room 2.7.0**. A `SupportSQLiteDatabase` bridge (`room-sqlite-wrapper`, `getSupportWrapper()`) from **Room 2.8.0** (10 Sep 2025). Latest 2.x: 2.8.5 (9 Sep 2026) | Room release notes |
| Licence | Apache-2.0 (androidx) + SQLite public domain | — |
| APK size added | Not found in the docs. Measure with APK Analyzer (estimate about 1–2 MB per ABI, by analogy with requery) | — |
| Maintained | Yes. Google, releases monthly in 2026 | release notes |
| Threading | Compiled in multi-thread mode: "connections opened by the driver are NOT thread-safe". Room manages a pool, raw use needs care | `BundledSQLiteDriver` reference |

**Why it is preferable**
- It is Google's own supported answer. The Android KMP docs call it "the recommended
  implementation". That makes it the strongest answer to A3: we used the official way.
- It is actively maintained, with the newest SQLite (3.53.4 against 3.32 on the A32), and it
  is the same SQLite on every phone. That removes the "different phone, different SQLite"
  worry behind B8.
- **FTS5 comes with it.** That closes the Head 6 gap (FTS4 only, no `bm25()`), which
  `core.md` requires to be fixed eventually. One migration fixes two gaps.
- For a test, the lead does not need to touch Room:
  `BundledSQLiteDriver().apply { addExtension(...) }.open(path)` works directly inside
  `VectorStorageSpikeTest`.

**Why it is not preferable**
- Adopting it in the app means **Room 2.6.1 → 2.8.x** and `setDriver(BundledSQLiteDriver())`.
  All our raw SQL is on `SupportSQLiteDatabase`. Once a driver is set, the docs say
  `SupportSQLiteDatabase` usages "need to be refactored with SQLite Driver APIs". The 2.8
  `getSupportWrapper()` bridge avoids a rewrite, but it is a compatibility layer, and
  transactions and cursors through it must be re-tested.
- The app's SQLite gets a little bigger (exact size not published).
- It does not supply sqlite-vec itself. We still need a good `.so` (see R5).

---

## R2 · requery `sqlite-android`

**How it works.** A copy of `android.database.sqlite` (from AOSP) with its own, newer SQLite
inside. Imports change from `android.database.sqlite.*` to `io.requery.android.database.sqlite.*`.
Extensions are registered through `SQLiteDatabaseConfiguration.customExtensions` with
`SQLiteCustomExtension(path, entryPoint)`. **Room plugs in through
`RequerySQLiteOpenHelperFactory`**, which implements `SupportSQLiteOpenHelper.Factory` and
accepts `ConfigurationOptions`, so the extension can be added there.

| Fact | Value | Source |
|---|---|---|
| Coordinates | `com.github.requery:sqlite-android:<ver>` on **JitPack** (not Maven Central) | README |
| Version | README shows 3.50.4. The newest Git tag / JitPack build is 3.49.0 | README; GitHub tags; JitPack API |
| Extension loading compiled in | Yes: no `SQLITE_OMIT_LOAD_EXTENSION`, and README lists "Loadable extension support" | `jni/sqlite/Android.mk` |
| FTS5 / RTREE / JSON1 | All enabled | same file |
| Min Android | API 21 | README |
| Licence | Apache-2.0 | README |
| APK size added | ~1.7 MB arm64-v8a, ~1.2 MB armeabi-v7a | README |
| Maintained | Slowing: last push 14 Oct 2025, about 1,140 stars, not archived | GitHub API |
| Room needed | **Works with Room 2.6.1 as it is**, through `openHelperFactory(...)` | README + `RequerySQLiteOpenHelperFactory.java` |

**Why it is preferable**
- **Lowest cost for the app.** Room stays at 2.6.1, and every `SupportSQLiteDatabase` call
  in `VideoVectors.kt` and the other files keeps working. It is one builder line plus the
  extension option.
- FTS5 is included, as with R1.
- Its size is documented and small.

**Why it is not preferable**
- Third-party, and maintenance is slowing (no push for about a year). The README and the
  published build disagree on the version.
- It is served from JitPack, which builds from Git on demand. That is a weaker supply chain
  than Google Maven.
- It is a fork of an old Android API copy, so its behaviour may drift from the platform's.

---

## R3 · SQLCipher for Android (`net.zetetic:sqlcipher-android`)

**How it works.** An encrypted SQLite build with its own copy of the Android database API.
Its native connection code calls `sqlite3_enable_load_extension(db, 1)` on every connection,
and it is compiled with `-DSQLITE_ENABLE_LOAD_EXTENSION`. So plain SQL
`SELECT load_extension('<path>/libvec0.so', 'sqlite3_vec_init')` should work. Room 2
integration is through `SupportOpenHelperFactory(password)`.

| Fact | Value | Source |
|---|---|---|
| Version | 4.20.0 (README); it depends on `androidx.sqlite:sqlite:2.7.0` | README |
| Extension loading | Enabled at build and at every connection open | `Android.mk`; `android_database_SQLiteConnection.cpp` line ~234 |
| FTS5 / RTREE / JSON1 | All enabled | `Android.mk` |
| Licence | BSD-style (Zetetic LLC) for the community edition | LICENSE |
| Maintained | Yes: last push 27 Oct 2026; supports Room 2 and Room 3 | GitHub API; README |
| Size | Larger than R1/R2 because the crypto code is linked in. Exact figure not found | — |

**Why it is preferable**
- It loads extensions *and* encrypts the database at rest. For a "second brain" that holds a
  person's whole day, encryption is a real privacy argument. It is not on the card, but it
  fits the project goal ("nothing leaves the device").
- Actively maintained, and works with Room 2.6-style `SupportSQLiteOpenHelper.Factory`.

**Why it is not preferable**
- Encryption is extra work and extra risk. It needs key management (where does the password
  live?) and adds a CPU cost on every page read. Vector scans read many pages.
- Its extension loading comes as a side effect of its build, not as a documented feature,
  so we would be relying on undocumented behaviour.
- It solves a problem (encryption) that no card asked for. Under the Ponytail rule in
  `core.md`, it is not the simplest route.

---

## R4 · Own NDK build: SQLite amalgamation + `sqlite-vec.c`, statically linked

**How it works.** Compile `sqlite3.c` and `sqlite-vec.c` into one `.so` with the NDK. Register
the module at start-up with `sqlite3_auto_extension(sqlite3_vec_init)`, so no runtime loading
is needed at all. Wrap it with our own JNI, or with a custom `SupportSQLiteOpenHelper`.

**Why it is preferable**
- Full control over everything: NEON on (see R5), 16 KB alignment, only the flags we need.
- No dynamic loading at all, so file paths and `dlopen` cannot fail.

**Why it is not preferable**
- We would own a native build and a JNI database layer. That is the largest effort and the
  largest bug surface of all the routes. R1 and R2 already give us a maintained SQLite with
  loading turned on.
- It is not justified unless R1 and R2 both fail on the phone. Keep it as plan C.

---

## R5 · Where the sqlite-vec `.so` comes from (needed by R1–R3)

**Prebuilt.** sqlite-vec **v0.1.9** (31 Mar 2026, marked Latest; v0.1.10-alpha.4 is a
pre-release) publishes Android loadables for `aarch64`, `armv7a`, `i686` and `x86_64`, each
about 60 KB compressed. The entry point is `sqlite3_vec_init`. Licence: MIT / Apache-2.0 dual
(the repo reports Apache-2.0). Mobile docs: "As of `v0.1.2`, we publish pre-compiled loadable
library for both platforms". An `.aar` is "planned", with an open issue (#102).

**Two problems found in the prebuilt, both checked on 5 Nov 2026:**

| Problem | Evidence | Effect on Eykon |
|---|---|---|
| **4 KB page alignment** | `readelf -lW vec0.so`: every `LOAD` segment aligned `0x1000`. Android requires ≥ `0x4000` (2¹⁴) on 16 KB devices ([evidence](evidence/prebuilt-so-alignment.txt)). Fix PR #254 is open and unmerged, and a comment on 9 Oct 2026 reports v0.1.10-alpha.4 is still 4 KB-aligned. | It loads on today's 4 KB phones (both of ours). On a 16 KB device (Pixel 8/9 with the "Boot with 16KB page size" developer option, and future phones) it runs only in compatibility mode or fails. Google Play blocks updates without 16 KB support **from 1 Feb 2027** for apps targeting API 35+ (ours is 35). |
| **No NEON SIMD on Android** | The `Makefile` adds `-DSQLITE_VEC_ENABLE_NEON` only for `Darwin arm64`. The Linux block is inside `ifeq ($(findstring android,$(CC)),)`, so Android cross-builds get no SIMD. PR #339 (open) reports a 3–5× speedup from NEON on Linux arm64. | On the phone, sqlite-vec would run its **scalar** distance loop. It may be no faster than the lead's `blob_memory_fast` Kotlin loop, so it must be measured before anyone assumes it is quicker. |

**The fix for both: build the `.so` ourselves.** sqlite-vec is a single C file. Build it with
**NDK r28 or newer** (16 KB-aligned by default; on r27c add
`-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384`) and with
`-DSQLITE_VEC_ENABLE_NEON`. It goes in `jniLibs/arm64-v8a/libvec0.so` (the `lib<name>.so`
naming matters, issue #68). Check it with `check_elf_alignment.sh` or APK Analyzer.

---

## Side-by-side

| | R1 bundled | R2 requery | R3 SQLCipher | R4 own NDK |
|---|---|---|---|---|
| Who maintains it | Google | One OSS project, slowing | Zetetic, active | Us |
| Room change for the app | 2.6.1 → 2.8.x + wrapper | **none** | none (Room 2 factory) | custom helper |
| Change needed just to *test* on the phone | none (open the driver in the test) | none (open requery DB in the test) | none | large |
| SQLite version | 3.53.4 | 3.49–3.50.4 | recent (4.20.0) | any |
| FTS5 bonus | yes | yes | yes | if we enable it |
| Extension API | documented (`addExtension`) | documented (`customExtensions`) | side effect | not needed |
| Extra risk | wrapper behaviour | supply chain, maintenance | key management, crypto cost | everything |
| Effort to adopt in the app | medium | **low** | medium | high |
| Long-term fit | **best** | fair | fair if encryption is wanted | poor |
