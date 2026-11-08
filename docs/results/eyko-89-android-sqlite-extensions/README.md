# EYKO-89 · Why Android blocks SQLite extensions, and every way around it

Research card EYKO-89 (Head 2), done 5 November 2026 by Taha Ahmed. It answers supervisor
questions **A2**, **A3** and **B7**. Every claim has a source in [sources.md](sources.md) or
says "not found". Raw fetches and the `readelf` checks are in [evidence/](evidence/).

> The card names `docs/results/<date>-android-sqlite-extensions.md` as the deliverable. The
> project owner asked for a folder instead, so this README is that deliverable and the
> numbered files hold the detail.

## Answers in brief

**A2 · sqlite-vec problem or Android problem? Android.**
Android's system SQLite is built with `-DSQLITE_OMIT_LOAD_EXTENSION`. That line is in AOSP
`external/sqlite/dist/Android.bp` and is unchanged from Android 11 to the current main
branch, so `load_extension()` does not exist. The 4 Nov phone run showed that even a made-up
extension fails the same way, so the cause is not sqlite-vec. The same build file also
explains why the phone has FTS4 but no FTS5 or RTREE. → [01](01-why-android-blocks-extensions.md)

**A3 · Apps can ship their own SQLite. Did you try?**
Not yet on a phone; that test is the lead's card. Three ready-made SQLite builds load
extensions on Android: androidx `sqlite-bundled` (Google, `addExtension` since 2.6.0),
requery `sqlite-android`, and SQLCipher. A fourth option is our own NDK build. Each one is
compared with sources, pros and cons. → [02](02-routes-to-load-extensions.md)

**B7 · Brute force won't scale. What is the plan?**
New phone data (4 Nov) shows the **Java heap** fails first, not speed. Three float32 tables
run out of memory at 50k rows on both phones, while the fast loop searches 100k rows in 39 ms
(Pixel) and 91 ms (A32). The plan has three steps:
1. Move vectors off the heap and store them as int8 or f16, keeping exact search.
2. Measure sqlite-vec for memory and file size.
3. Use usearch (HNSW, memory-mapped) beyond about 200k rows.
→ [03](03-vector-search-options.md)

## Recommended

| For | Pick | Why, in one line |
|---|---|---|
| The lead's phone test | **R1 · `BundledSQLiteDriver.addExtension` + a sqlite-vec `.so` we build with NDK r28 and NEON** | Google-supported and testable without touching Room; brings FTS5 too |
| App adoption, if R1's Room upgrade is too heavy | R2 · requery | Works with Room 2.6.1 unchanged; maintenance is slowing |
| Laptop fallback index (EYKO-91) | **usearch** | Approximate + memory-mapped + i8/f16 + official Android arm64 build |
| Before any of these | Off-heap int8 / f16 vectors (no new library) | Fixes the measured out-of-memory error directly |

Scoring, test steps and pass marks → [04](04-recommendation.md).

## Two findings that were not on the card

1. **The sqlite-vec Android prebuilt is 4 KB page-aligned** (`readelf`: `LOAD … 0x1000`), and
   so is the usearch prebuilt. Both load on our two phones today, but not cleanly on 16 KB
   devices. Google Play blocks such updates from 1 Feb 2027 for targetSdk 35+, which is ours.
   Fix: build the `.so` ourselves with NDK r28+. Open PR upstream: sqlite-vec #254.
2. **The sqlite-vec Android build has no NEON SIMD.** Its Makefile enables NEON only on macOS.
   On the phone it would run scalar code, so it must not be assumed faster than our own
   fast loop. It has to be measured.

## Files

| File | Contents |
|---|---|
| [01-why-android-blocks-extensions.md](01-why-android-blocks-extensions.md) | A2: the AOSP line, which branches have it, the 4 Nov log explained |
| [02-routes-to-load-extensions.md](02-routes-to-load-extensions.md) | A3: R1–R5, each with facts, pros and cons, and a side-by-side table |
| [03-vector-search-options.md](03-vector-search-options.md) | B7: which limit comes first, O1–O7 with pros and cons |
| [04-recommendation.md](04-recommendation.md) | Weighted scoring, the route for the lead, steps and pass marks, things noticed |
| [sources.md](sources.md) | Sources table (title, link, date read) and what was not found |
| [evidence/](evidence/) | Raw AOSP / androidx / requery / SQLCipher flag greps; `readelf` alignment output |

## How to check this yourself

```bash
# A2: the flag in Android's SQLite build (any branch)
curl -s "https://android.googlesource.com/platform/external/sqlite/+/refs/heads/main/dist/Android.bp?format=TEXT" | base64 -d | grep -n OMIT_LOAD_EXTENSION

# A3: androidx bundled SQLite has no such flag, and has FTS5
curl -s "https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/sqlite/sqlite-bundled/build.gradle?format=TEXT" | base64 -d | grep -n "OMIT_LOAD_EXTENSION\|FTS5\|sqliteVersion"

# 16 KB finding: the prebuilt's alignment (0x1000 = 4 KB)
mkdir -p /tmp/vec && cd /tmp/vec && curl -sL https://github.com/asg017/sqlite-vec/releases/download/v0.1.9/sqlite-vec-0.1.9-loadable-android-aarch64.tar.gz | tar xz && readelf -lW vec0.so | grep LOAD
```
