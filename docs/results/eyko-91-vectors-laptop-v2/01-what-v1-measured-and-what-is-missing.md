# 1 · What the laptop has measured so far, and what is missing

Plan for card EYKO-91, written 5 November 2026. This file is about the starting point. The
benchmark design is in [02](02-benchmark-design.md).

## v1: the EYKO-31 laptop spike (12 October 2026)

`src/benchmarks/vector_storage_spike.py`, run with `task spike-laptop-vectors`.
Write-up: `docs/results/2026-10-12-eyko-31-vector-storage.md`.

| | v1 |
|---|---|
| Machine | "development laptop, 12 CPU threads" (the lead's Windows laptop, `D:\eykon-cache`) |
| Software | Python 3.10.6, SQLite 3.37.2, numpy 2.2.6, sqlite-vec 0.1.9 |
| Vectors | 512-d random unit vectors, seed 31 |
| Sizes | 5,000 and 20,000 |
| Runs | **one** run of 20 queries, no warm-up; median and worst only |
| Methods | BLOB read from SQLite per query; BLOB in memory (numpy); sqlite-vec float32 |
| Correctness | **not checked**. The script has a `# same top-1 from both methods?` comment, but no check after it |
| Memory | "peak RSS" read from `peak_wset`, which exists **only on Windows**. On Linux the same line prints current RSS |

v1 results (median / worst ms):

| Method | 5k | 20k |
|---|---|---|
| BLOB read + dot | 24.13 / 33.64 | 91.78 / 103.32 |
| BLOB in memory (numpy) | 0.23 / 0.48 | 1.49 / 1.74 |
| sqlite-vec 0.1.9 | 8.38 / 9.56 | 30.95 / 34.95 |

## What has happened on the phones since then

| Date | Card | What it added | Raw files |
|---|---|---|---|
| 3 Nov | EYKO-90 | Phone sweep 1k → 300k, 5 runs × 20 queries, shared CSV format, random vectors | `docs/results/vectors/*-2026-11-03-sweep.csv` |
| 4 Nov | EYKO-100 | "Real" vectors, the faster loop (`blob_memory_fast`, same top 20 on 400 of 400), memory with all three tables (out of memory at 50k) | `*-2026-11-04-sweep-real.csv`, `*-2026-11-04-memory.csv` |
| 4 Nov | EYKO-102 | The faster loop in the app: whole search 4.3× faster, 2,400 of 2,400 hits identical | Head 7 |

So the laptop is now **behind the phones**: the phones have 5 runs, 1k–100k and a correctness
check, while the laptop has none of these.

## What the card asks for, against what exists

| Card step | Today | Gap |
|---|---|---|
| 1 · new script `vector_storage_v2.py`, `task vectors-laptop-v2` | v1 only | new script, v1 kept as it is |
| 2 · sizes 1k–300k, 1 warm-up + 20 queries × 5 runs, median / p95 / worst | 5k, 20k; 1 run; no p95 | all of it |
| 3 · methods: BLOB disk, BLOB numpy, **plain Python loop**, sqlite-vec f32, **sqlite-vec int8**, **one approximate index** | first three only (minus the Python loop) | four new methods |
| 4 · recall@20 against exact numpy | never checked | all methods |
| 5 · **real vectors** + random, `source_vectors` column | random only | see [03](03-vector-sources.md): the card's suggested source raises a licence problem |
| 6 · file size and peak RSS per method and size | file size yes; RSS Windows-only | per-method memory, measured in a clean process |
| 7 · shared CSV to `docs/results/vectors/laptop-<date>.csv` | no CSV | new; naming question in [02](02-benchmark-design.md) |

## Also asked of this card since it was written

- **EYKO-109** (option O1, vectors outside Java memory) expects EYKO-91 to measure how much
  accuracy **float16** and **int8** lose. These are cheap to add as numpy methods.
- **The EYKO-89 recommendation** names **usearch** as the approximate index to test.
- **B5** ("chip or code?"): the Head 2 doc says the laptop "has not been rerun with the new
  loop". A plain-Python loop and **single-thread numpy** on the laptop separate the two.

## Things that change how the numbers can be compared

1. **This is a different laptop.** v1 ran on the lead's 12-thread laptop. This plan runs on
   Taha's: Intel Core i5-10310U (4 cores / 8 threads, AVX2 + FMA), 15 GB RAM, Linux, Python
   3.10.12. **v2 reruns every v1 method on this machine**, so laptop comparisons stay within one
   machine. Its numbers must not be set against v1's 12-thread numbers as if they were the same
   laptop.
2. **Only 15 GB of disk is free** on this laptop, which limits any real-image dataset ([03](03-vector-sources.md)).
3. **`task` (go-task) is not installed here.** It is needed to run `task vectors-laptop-v2`.
   Until it is, the same command runs through `uv run`.
