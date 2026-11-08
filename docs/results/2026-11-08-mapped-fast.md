# Memory-mapped vectors at today's speed (EYKO-114)

**Date:** 8 November 2026 · **By:** Rafique · **Card:** EYKO-114 · **Phone:** Samsung A32, cable in for every mode ·
**Builds on:** EYKO-109 (Zara's storage modes) · **Gap:** G20 · **Supervisor questions:** B4, B7

**Verdict: `MAPPED_NATIVE` passes every mark, so it is the candidate to adopt.** The vectors stay in a memory-mapped
file and are scored in place by a small NEON C function. The scores are **bit-identical** to today's search, three
tables load at 50k and at 100k rows with **4–5 MB of Java memory** (today runs out of memory at 50k), and it is only
**+0.6 % to +1.5 %** slower than today. The cheaper option, `MAPPED_BLOCK`, stays exact but is +8 to +10 %, right on the line.

**Second finding, bigger than the first:** about **85 % of every search today is not scoring.** It is the check
`VideoVectors.scores` runs on every search to see whether the table changed, `SELECT COUNT(*), IFNULL(MAX(id), 0)`, and
`COUNT(*)` reads the whole table: **479 ms of the 565 ms** search at 100k, and 114 of 115 ms at 20k. `MAX(id)` alone
takes 0.13 ms. This belongs to Head 7 (search speed) and is proposed as its own card.

## What was tested

Zara's EYKO-109 code (`VectorBlock.kt`, `VideoVectors.kt`, `OffHeapVectorTest.kt`, branch `zara/eyko-109-vectors-off-heap`)
plus two new modes in `VectorMode`:

| Mode | What it does | Code |
|---|---|---|
| `HEAP_F32` | today: one Java `FloatArray` per table | unchanged |
| `MAPPED_F32` | EYKO-109: the vectors in a mapped file next to the database, **one row at a time** copied to a scratch array, then `dot()` | unchanged |
| `MAPPED_BLOCK` (option 1) | the same mapped file, **1,024 rows (2 MB) per copy** into one reusable array, then the same `dot()` | `VectorBlock.scoreAll` |
| `MAPPED_NATIVE` (option 2) | the same mapped file, scored **in place** by C code with NEON, no copy | `android/app/src/main/cpp/eykonvec.c`, `VectorNative` |

**How `MAPPED_NATIVE` stays exact:** today's `dot()` keeps four running sums, one per position `i % 4`, and returns
`(s0 + s1) + (s2 + s3)`. One NEON register holds exactly those four sums. The C code multiplies and adds as two separate
steps (`vmulq_f32`, `vaddq_f32`), never fused, and is built with `-ffp-contract=off`. The disassembly has 0 `fmla` /
`fmadd` instructions, 5 `fmul` and 9 `fadd`. It scores 4 rows at once so the CPU can overlap them, and each row keeps
its own sum order.

**Library:** `libeykonvec.so`, built by `task build-vector-native` (`src/benchmarks/build_vector_native.py`) with NDK r28c,
`-O3 -ffp-contract=off`, 16 KB pages: 6,376 B, every LOAD aligned `0x4000`, JNI symbol exported, SHA256
`95f1122d0aa7823f748130c9934d882de8a3cc8fa439da467a79454dfa661451`. It is built into
`android/app/src/main/jniLibs/arm64-v8a/` (git-ignored) and is in the app APK as `lib/arm64-v8a/libeykonvec.so`.

**Run:** A32 (SM-A325F), Android 13, **cable in for every mode** (EYKO-112: on battery the A32 is 1.2–1.4× slower, so modes are only
compared within one power state). Battery 100 %, temperature 27.6 → 28.0 C. Real own-clip vectors plus noise, 512-d image
table, 1 warm-up + 20 queries × 5 runs. The commit column says `d7af093+eyko114-uncommitted`; the code that ran is in the commit
that adds this file. **Check:** all 60 timed CSV rows match the raw log.

## Speed: whole `VideoVectors.scores()` call, median of 5 run medians (range of the 5)

| Rows | `HEAP_F32` (today) | `MAPPED_F32` | `MAPPED_BLOCK` | `MAPPED_NATIVE` |
|---|---|---|---|---|
| 20,000 | 115.2 (114.9–115.3) | 129.3, **+12.2 %** | 126.8, **+10.1 %** | **115.9, +0.6 %** |
| 50,000 | 283.7 (283.4–284.0) | 319.2, +12.5 % | 307.3, +8.3 % | **286.2, +0.9 %** |
| 100,000 | 565.2 (565.1–565.4) | 636.7, +12.6 % | 613.0, +8.5 % | **573.8, +1.5 %** |

Exact answers: **every mode gave scores bit-identical to `HEAP_F32` on 20 of 20 queries at every size**, so recall@20 = 1.0
(400 of 400). The first search, which builds the table's copy, takes about the same in every mode: 1.6–1.7 s at 20k,
6.7–7.1 s at 50k, 23–24 s at 100k.

## Memory: three tables (image 512, text 384, audio-sized 512), n rows each

Java heap after loading / total PSS after (MB) / tables loaded. PSS before was 54 MB, native heap 11 MB throughout.

| Rows each | `HEAP_F32` | `MAPPED_F32` | `MAPPED_BLOCK` | `MAPPED_NATIVE` |
|---|---|---|---|---|
| 20,000 | 116 / 162 / 3 | 3 / 162 / 3 | 3 / 162 / 3 | 3 / 162 / 3 |
| 50,000 | 183 / 226 / **2** (out of memory) | 4 / 324 / 3 | 4 / 324 / 3 | **4 / 324 / 3** |
| 100,000 | 208 / 250 / **1** (out of memory) | 5 / 594 / 3 | 5 / 594 / 3 | **5 / 594 / 3** |

PSS for the mapped modes includes the mapped file's pages. They are file-backed, so Android can drop and re-read them,
and they do not count toward the 268 MB Java limit. EYKO-109 measured what that costs after 5 minutes in the background
(first search 3.8× slower on the Infinix).

## Against the pass marks (written before the run)

| Mark | `MAPPED_BLOCK` | `MAPPED_NATIVE` |
|---|---|---|
| Exact (bit-identical to `HEAP_F32`) | pass, 20 / 20 at every size | **pass**, 20 / 20 at every size |
| Three tables at 50k and 100k without running out of memory | pass | **pass** |
| No more than 10 % slower at 20k, 50k, 100k | **fails at 20k** (+10.1 %), passes 50k and 100k | **pass** (+0.6, +0.9, +1.5 %) |

## Where the time goes: the change check on every search

`VideoVectors.scores` asks SQLite on every search whether the table changed, so it knows whether its cached copy is still good:
`SELECT COUNT(*), IFNULL(MAX(id), 0) FROM <table>`. Timed alone on the A32 (`OffHeapVectorTest#changeCheckCost`, median of 20,
`proof/a32-2026-11-08-eyko114-changecheck-logcat.txt`):

| Query | 20,000 rows | 100,000 rows |
|---|---|---|
| `SELECT COUNT(*), IFNULL(MAX(frame_id), 0)` (today) | **113.8 ms** | **479.3 ms** |
| `SELECT COUNT(*)` | 118.8 ms | 454.7 ms |
| `SELECT IFNULL(MAX(frame_id), 0)` | 0.19 ms | 0.13 ms |
| `SELECT MAX(rowid)` | 0.14 ms | 0.12 ms |

- `COUNT(*)` reads every row of the table, and each row holds a 2 KB vector BLOB, so the whole table is read on every
  search. `MAX` uses the key and reads one path down the tree.
- So of today's 565 ms at 100k, about 479 ms is the check and about 86 ms is the scoring. That fits the 91 ms the
  scoring loop alone took in EYKO-100.
- **Proposed (Head 7):** replace the `COUNT(*)` in the check with something that does not read the table. That is either a change
  counter the app bumps when it inserts or deletes vectors, or `MAX(id)` plus clearing the cache whenever rows are deleted. It
  could make the app's search about 5–6× faster at 100k on the A32 (about 565 → about 90 ms) with the same answers. Not built or
  measured here.

## What adopting `MAPPED_NATIVE` still needs (not done here)

1. Switch the app's default mode from `HEAP_F32` to `MAPPED_NATIVE`, with a fallback to `HEAP_F32` if the library fails to load.
2. Write the vector file once and keep it up to date, instead of rebuilding it on every load as EYKO-109 does (the 23 s
   first search at 100k), and delete it when its table goes.
3. Accept the storage cost: a second copy of the vectors next to the database (about 563 MB at 100k rows × 3 tables,
   EYKO-109), unless the file replaces the BLOBs. That conflicts with "same tables on laptop and phone" and is EYKO-98's call.
4. Make scoring thread-safe. Native scoring reads the mapped memory without the buffer's position, so it is already safe there;
   `MAPPED_BLOCK` / `MAPPED_F32` move a shared position.
5. Run the A32 hot and low-battery runs and the Pixel, as for every Head 2 result.

## Limits

- One phone (A32), cable in, one session. The Infinix and Pixel were not run.
- The background-kill behaviour of the mapped file was measured in EYKO-109 (Infinix), not again here.
- The change-check fix is a proposal, not measured.

## Files

- Code: `android/app/src/main/cpp/eykonvec.c`, `VectorBlock.kt` (`MAPPED_BLOCK`, `MAPPED_NATIVE`, `VectorNative`), `VideoVectors.kt`
  (mapped modes), `OffHeapVectorTest.kt` (two mode names, `changeCheckCost`), `src/benchmarks/build_vector_native.py`, Taskfile `build-vector-native`.
- CSVs: `docs/results/vectors/offheap/a32-2026-11-08-eyko114-speed-SM_A325F-20261108-1825.csv`, `…-memory-SM_A325F-20261108-1838.csv`.
- Raw logcat: `docs/results/vectors/proof/a32-2026-11-08-eyko114-speed-logcat.txt` (also holds the memory run), `…-memory-logcat.txt`,
  `…-changecheck-logcat.txt`; device readings `…-eyko114-device.txt`; screenshot `…-eyko114-logcat.png`.
