# sqlite-vec for Android, built by us (EYKO-104, route R5)

**Date:** 7 November 2026 · **By:** Rafique · **Card:** EYKO-104 · **Feeds:** EYKO-105 (R1), 106 (R2), 107 (R3) · **Supervisor questions:** A3, B7

**Verdict:** we now have our own `libvec0.so` for arm64 phones, in a NEON and a no-NEON build. Both
pass every check the card asks for. They are aligned for 16 KB pages, export `sqlite3_vec_init`,
and need only `libc`, `libm` and `libdl`. Rebuilding gives byte-identical files. **They have not been
loaded on a phone yet.** Windows cannot load an Android file, so the first real load is R1 (EYKO-105).

## Why we built our own

EYKO-89 checked the ready-made file (`sqlite-vec-0.1.9-loadable-android-aarch64.tar.gz`) and found
two problems (`docs/results/eyko-89-android-sqlite-extensions/evidence/prebuilt-so-alignment.txt`,
on Taha's branch):

1. It is aligned for 4 KB pages (`0x1000`). 16 KB-page phones need `0x4000`, and Google Play
   blocks such updates for targetSdk 35+ from 1 Feb 2027. Ours is targetSdk 35.
2. It has no NEON. The sqlite-vec `Makefile` turns NEON on only for macOS arm64.

All three route cards load this one file, so a route's result can't be blamed on a bad file.

## What was used

| Item | Value | Checked how |
|---|---|---|
| NDK | r28c, `Pkg.Revision = 28.2.13676358` | Zip SHA1 `086bba43…ba1d` = Google's `repository2-3.xml` |
| sqlite-vec | v0.1.9 amalgamation, commit `e9f598abfa0c06b328d8fe5da9c3760cce74be10` | Tag `v0.1.9` points at that commit (GitHub API); `sqlite-vec.h` names the same `SQLITE_VEC_SOURCE`; tarball SHA256 `3acd67cb…cf61` is pinned in the script |
| SQLite headers (`sqlite3ext.h`) | 3.54.1 amalgamation | SHA3-256 `92281c86…8e30` = sqlite.org download page, pinned in the script |
| Target | `aarch64-linux-android31` (our minSdk) | — |

Only the headers come from SQLite. The extension calls whichever SQLite loads it, through its
function table: Google's bundled 3.53.4 in R1, requery in R2, SQLCipher in R3.

## How to rebuild

```bash
task build-sqlite-vec-android
```

The script is `src/benchmarks/build_sqlite_vec_android.py`. It fetches both source archives if
they're missing and refuses any hash that doesn't match the pinned one. It then builds both
variants, runs the checks, and rewrites the evidence folder. Pass `-- --ndk <dir>` to use another
NDK r28+. The exact compile command, as it ran (no-NEON is the same without the `-D` flag):

```
clang.exe --target=aarch64-linux-android31 -O3 -fPIC -shared -Wall -Wextra
  -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384 -DSQLITE_VEC_ENABLE_NEON
  -I<sqlite-amalgamation-3540100> sqlite-vec.c -lm -o libvec0.so
```

These are the same flags as sqlite-vec's own `loadable` target, plus the Android target. r28
already aligns for 16 KB by default. The two `-z` flags make that explicit, so an older NDK would
still give a correct file. The compile gives 0 warnings under `-Wall -Wextra`.

## Results

| Check (card step 5) | NEON | no-NEON |
|---|---|---|
| Every `LOAD` aligned `0x4000` | ✅ 4 of 4 | ✅ 4 of 4 |
| `sqlite3_vec_init` exported (`FUNC GLOBAL DEFAULT`) | ✅ | ✅ |
| `NEEDED` | `libm.so`, `libdl.so`, `libc.so` | same |
| NEON path compiled in (preprocessor: calls to `*_neon(`) | 8 | 0 |
| Size | 145,936 B | 142,760 B |
| SHA256 | `264ec3266849dc7cd9e1454abacbadae4cc900f55888c7311522f66297fc3e46` | `ccd7178d98dbe081b63688a9259ab40528201dba5b22a9524760e8bde7e38329` |

Raw output: [`readelf-neon.txt`](2026-11-07-sqlite-vec-android-build/readelf-neon.txt),
[`readelf-no-neon.txt`](2026-11-07-sqlite-vec-android-build/readelf-no-neon.txt),
[`SHA256SUMS.txt`](2026-11-07-sqlite-vec-android-build/SHA256SUMS.txt).

**Checking the checks:**
- **Negative control.** The same source built with `-Wl,-z,max-page-size=4096` gives `LOAD … 0x1000`
  on all 4 segments, which the script's check rejects. So the `0x4000` result really comes from our
  flags and the NDK.
- **Reproducible.** Three rebuilds gave the same two SHA256s.

**Where the files are** (kept out of git, like the models):
`D:\eykon-cache\sqlite-vec-android\out\neon\arm64-v8a\libvec0.so` and
`D:\eykon-cache\sqlite-vec-android\out\no-neon\arm64-v8a\libvec0.so`. Route cards copy one of them into
`android/app/src/androidTest/jniLibs/arm64-v8a/` and check its SHA256 against the table above.

## Things route cards must know

1. **NEON only speeds up L2 and L1 distance, not cosine.** In `sqlite-vec.c` v0.1.9, NEON code
   exists for `distance_l2_sqr_float`, `distance_l2_sqr_int8`, `distance_l1_int8` and
   `distance_l1_f32`. `distance_cosine_float` is plain C in both builds. Our vectors are
   normalised, so L2 ranks results exactly as dot product does. R1–R3 should create the `vec0`
   table with the default L2 metric, or NEON does nothing.
2. **The no-NEON build is not fully scalar.** NEON is always present on arm64, and clang `-O3`
   vectorises some loops by itself (473 4-lane float instructions against 655 in the NEON build).
   The phone numbers will show the gain from sqlite-vec's own NEON code. They won't be a
   NEON-versus-no-SIMD comparison.
3. **Check the file on the phone.** After loading it, run `SELECT vec_version(), vec_debug()`. That
   should give `v0.1.9`, and the build line should read `neon` for the NEON file and be blank for
   the other one (`SQLITE_VEC_DEBUG_BUILD` in `sqlite-vec.c`). That proves which file a run used.
   The default `vec0` metric is L2 (`sqlite-vec.c` line 2348).
4. **arm64 only.** All three phones (A32, Pixel 9 Pro XL, Infinix X670) are arm64-v8a, so no
   armeabi-v7a build was made (card step 3).

## Limits, said plainly

- Not loaded on any phone yet. That a phone accepts the file, plus the speed and recall numbers,
  belong to R1–R3.
- The card says the laptop had NDK r27c. It had no NDK installed, so r28c was downloaded fresh.
- Disk: the NDK takes about 2.5 GB on D:, which now has about 2 GB free.
