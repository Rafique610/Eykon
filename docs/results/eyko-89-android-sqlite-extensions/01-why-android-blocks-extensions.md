# 1 · Why sqlite-vec fails on Android (supervisor question A2)

> **Is it a sqlite-vec problem or an Android problem?**
> Android. The SQLite that ships with Android is compiled with extension loading removed.
> No extension of any kind can be loaded into it, and sqlite-vec is not to blame.

## The two errors, explained separately

Every run on both phones gives the same two errors (A32 on 12 Oct, 3 Nov and 4 Nov; Pixel on
3 Nov and 4 Nov):

| Error | What it means | Whose problem |
|---|---|---|
| `no such function: load_extension` | The SQL function that loads a `.so` does not exist in this SQLite build. | **Android.** It is compiled out (see the next section). |
| `no such module: vec0` | No virtual-table module named `vec0` has been registered. | Neither. It follows from the first error: `vec0` only exists after sqlite-vec has been loaded, and nothing could load it. Any SQLite without sqlite-vec gives this error. |

The lead's 4 Nov proof run shows the cause is general, not specific to sqlite-vec. It tried
to load an extension that does not exist (`load_extension('eyko_no_such_extension')`) and got
the same `no such function: load_extension`. Had loading been allowed, the error would have
been "cannot open shared object". (`docs/results/vectors/proof/*-2026-11-04-extensions-logcat.txt`)

## The line in Android's source

Android's SQLite is built from AOSP `platform/external/sqlite`. The build file
`dist/Android.bp` defines the flags in `sqlite-minimal-defaults`:

```
cc_defaults {
    name: "sqlite-minimal-defaults",
    ...
        "-DSQLITE_OMIT_LOAD_EXTENSION",
```

`SQLITE_OMIT_LOAD_EXTENSION` is SQLite's own compile-time switch. It removes
`sqlite3_load_extension()`, `sqlite3_enable_load_extension()` and the SQL function
`load_extension()` from the build.

The library the OS ships inherits it through this chain:

`libsqlite` → `defaults: ["sqlite-defaults", …]` → `sqlite-defaults` →
`defaults: ["sqlite-minimal-defaults"]` → `-DSQLITE_OMIT_LOAD_EXTENSION`

**The same line is present in every release branch checked:**

| AOSP branch | Line in `dist/Android.bp` | Our phone on it |
|---|---|---|
| `android11-release` | 36 | — |
| `android13-release` | 66 | Samsung A32 (Android 13, SQLite 3.32.2) |
| `android14-release` | 66 | — |
| `android15-release` | 66 | — |
| `android16-release` | 67 | — |
| `main` (newest) | 67 | Pixel 9 Pro XL runs Android 17 (SQLite 3.50.6) |

Raw output: [`evidence/aosp-android-bp-flags.txt`](evidence/aosp-android-bp-flags.txt).

**The Java layer adds nothing on top.** `android.database.sqlite` is a JNI wrapper
(`frameworks/base/core/jni/android_database_SQLiteConnection.cpp`). Its 1,036 lines open the
database with `sqlite3_open_v2` and never mention "extension". The public `SQLiteDatabase`
class has no `enableLoadExtension` or `loadExtension` method. (Desktop Python, by contrast,
has `Connection.enable_load_extension`, which is why the laptop spike worked.)

## The same file explains the rest of the 4 Nov proof log

| Line in the phone log | Explained by `dist/Android.bp` |
|---|---|
| `built-in module: fts4 works` | `-DSQLITE_ENABLE_FTS3`, `-DSQLITE_ENABLE_FTS4` are set |
| `built-in module: fts5 failed: no such module: fts5` | No `SQLITE_ENABLE_FTS5` in the file |
| `built-in module: rtree failed` | No `SQLITE_ENABLE_RTREE` in the file |
| `compile options (extension / fts / rtree): [none listed]` | `-DSQLITE_OMIT_COMPILEOPTION_DIAGS` is set, so `PRAGMA compile_options` returns nothing |

This also explains a Head 6 limitation: the phone has FTS4 but no FTS5, so it has no
`bm25()`. That limit has the same cause, the platform's build flags.

## Is a newer Android going to fix it?

No sign of that. The flag is unchanged from Android 11 to `main`. Android's own docs say "the
version of SQLite depends on the version of Android" and that "some device manufacturers
include different versions of SQLite". Their table runs from SQLite 3.32 (API 31–33) to 3.50
(API 37). Newer Android brings a newer SQLite, but the same build flags. The two phones
confirm it: different Android versions (13 and 17) and SQLite versions (3.32.2 and 3.50.6)
gave the same failure.

## What this answer does not claim

- That no phone maker ships a SQLite with extensions enabled. Android's docs say makers can
  ship different versions. An app cannot rely on that, though, because the AOSP default
  removes loading, and our app must run on every phone.
- Anything about iOS. Not in scope.

## Answer for the defence, in one paragraph

> Android builds its system SQLite with `-DSQLITE_OMIT_LOAD_EXTENSION`. That line is in AOSP
> `external/sqlite/dist/Android.bp` and is unchanged from Android 11 to the current main
> branch. The `load_extension` function therefore does not exist, and no extension can be
> loaded: ours, sqlite-vec, or a made-up one, which we also tested. The `vec0` error follows
> from that. So it is an Android platform decision, not a sqlite-vec bug. Our two phones, on
> Android 13 and Android 17, fail identically.
