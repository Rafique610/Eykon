# 2 · Benchmark design

What the v2 script runs, how each number is taken, and where it is written. Sources of vectors:
[03](03-vector-sources.md). Library facts behind the choices: [04](04-libraries.md).

## Methods

Every method is given the same vectors and the same queries, and returns the top 20.

| # | `method` (CSV) | What it does | Sizes | Why |
|---|---|---|---|---|
| 1 | `blob_disk_dot` | Read every BLOB from SQLite, then numpy dot + top 20, on **every** query | ≤ 20k (as the phone's `diskMax`), skipped above with a `note` | v1 method; card step 3 |
| 2 | `blob_memory_numpy` | Matrix in memory once; `m @ q` (OpenBLAS, default threads) + `argpartition` | all | the laptop reference; card step 3 |
| 3 | `blob_memory_numpy_1t` | Same, numpy limited to **1 thread** (`threadpoolctl`) | all | fair against the one-thread phone loop (B5) |
| 4 | `blob_memory_pyloop` | Plain Python loops, no numpy | 1k, 5k (20k if under ~2 min per run) | card step 3: how much of the phone gap is code (B5) |
| 5 | `blob_memory_f16` | Matrix kept as float16 (½ the memory), dot in float32 in blocks | all | laptop half of **EYKO-109** (O1) |
| 6 | `blob_memory_i8` | int8 with **one scale per vector** (¼ the memory); each block widened to float32, dotted with the float32 query, then scaled (the byte × float loop a phone would run) | all | laptop half of EYKO-109 |
| 7 | `blob_memory_i8_rescore` | Method 6, then re-score its top 100 with float32 | all | EYKO-109's planned int8 design |
| 8 | `sqlite_vec_f32` | `vec0(e float[512] distance_metric=cosine)`, `MATCH ? AND k = 20` | all | v1 method; card step 3 |
| 9 | `sqlite_vec_int8` | `vec0(e int8[512] distance_metric=cosine)`, filled with `vec_quantize_int8(v, 'unit')` | all | card step 3 |
| 10 | `usearch_hnsw_c16_ef64` | usearch defaults (connectivity 16, expansion_search 64) | all | card step 3: the approximate index (EYKO-89's pick) |
| 11 | `usearch_hnsw_c16_ef256` | middle setting | all | recall against speed |
| 12 | `usearch_hnsw_c32_ef1024` | setting that reached 0.997 on random 20k | all | recall against speed |
| 13 | `usearch_exact_f32` | usearch `exact=True`, 1 search thread | all | a fast native brute force (B5) |

usearch searches use `threads=1`; building uses all threads and is timed separately.

## Sizes, runs and timing (card step 2)

- Sizes **1k, 5k, 20k, 50k, 100k, 300k** (S3: up to its largest size, target 100k).
- Per (source, size, method): build once, **1 warm-up query, then 5 runs × 20 queries**. Each query
  is timed alone with `time.perf_counter()`. Per run: median, p95, worst, which is one CSV row per run
  as on the phones.
- The queries are the same 21 for every method at a size (the first is the warm-up).
- Times are for search only. Load / insert / index build times go in `note`
  (`build_s=…; insert_s=…`).

## Correctness: recall@20 with ties (card step 4)

The reference is exact float32 numpy search on the same data. A returned item **counts as a hit if
its exact score is at least the exact 20th-best score minus 1e-6**. This counts ties: the probe
found identical vectors in the committed own-clip data, where a correct method can return either
copy ([04](04-libraries.md)).

- recall@20 = hits / 20, averaged over the 20 timed queries, written to the **`recall_at_20`** column.
- Methods 1, 2, 3, 4, 8 and 13 are exact by design and **must be 1.0**. Anything lower is a bug and
  stops the run.
- Methods 5, 6, 7, 9 and 10–12 report their recall. It is judged against the marks in [05](05-pass-marks-and-risks.md).

## Memory and file size (card step 6)

- **One fresh process per (source, size, method).** Peak memory only ever rises within a process,
  so measuring methods one after another in one process would give wrong numbers.
- `pss_mb` = **PSS** after the method has built and loaded (`psutil memory_full_info().pss`, works on
  Linux). This is the same measure the phones report, rather than the card's "peak RSS".
- Peak RSS (`resource.getrusage(RUSAGE_SELF).ru_maxrss`) and the process's PSS before loading go in
  `note` (`peak_rss_mb=…; pss_before_mb=…`), the same style the lead used in the 4 Nov memory CSV.
- `file_mb` = size of the SQLite file (methods 1, 8, 9) or the saved usearch index (10–12); empty
  for pure in-memory methods.
- `heap_mb` stays empty: there is no Java heap on the laptop.

## Shared CSV (card step 7)

Header: the card's shared format **plus the two columns already in use**. `note` is in every
phone CSV. `recall_at_20` is new; the plot script reads columns by name, so an extra column does
not break it.

```
device,android,sqlite_version,commit,date,method,dim,n,run,median_ms,p95_ms,worst_ms,pss_mb,heap_mb,file_mb,temp_c_start,temp_c_end,battery_pct,source_vectors,note,recall_at_20
```

- `device`: `laptop <cpu>` from `/proc/cpuinfo` (here `laptop i5-10310U`), or `--device`. `android` empty. `sqlite_version`: from Python's sqlite3.
- `commit`: `git rev-parse --short HEAD`, with `-dirty` if the tree has changes.
- `temp_c_start` / `temp_c_end`: CPU package temperature (`psutil.sensors_temperatures()`, coretemp).
  `battery_pct`: `psutil.sensors_battery()`; the note says whether the charger was in.
- **File name: one per source (owner's decision D2, 6 Nov).** The card says `docs/results/vectors/laptop-<date>.csv`. The Head 2
  figure script picks up only `*-sweep-real.csv`, so the laptop would not appear in the graphs EYKO-97
  draws. So: one file per source,
  `laptop-<date>-sweep.csv` (S1 random: the figure script finds random sweeps with `*-sweep.csv`, as the phones' 3 Nov files), `laptop-<date>-sweep-real.csv` (S2, the same data as the phones'
  real sweep) and `laptop-<date>-sweep-varied.csv` (S3).

## Code layout (keeps every `.py` under the 300-line rule in `core.md`)

| File | Job |
|---|---|
| `src/benchmarks/vector_storage_v2.py` | Command line, the loop over sources × sizes × methods, one process each, CSV rows |
| `src/benchmarks/_vector_methods.py` | One small class per method: `build(vectors, workdir)`, `search(query, k)`, `file_mb()` |
| `src/benchmarks/_vector_sources.py` | S1 / S2 / S3 vectors and queries; the recall-with-ties function |
| `src/benchmarks/embed_varied_frames.py` | Only for S3: stream videos → frames → MobileCLIP-S2 vectors (+ text queries) → one `.npy` file in the cache, never in git |
| `tests/test_vector_recall.py` | The recall rule on small hand-made cases: ties, an exact method = 1.0, a shuffled one < 1.0 |

`vector_storage_spike.py` (v1) stays untouched (card step 1).

Taskfile:

```
vectors-laptop-v2:
  desc: "EYKO-91 — laptop vector benchmark v2: 13 methods, 1k–300k, 5 runs × 20 queries, recall@20, PSS, shared CSV (sqlite-vec, usearch, threadpoolctl fetched for the run only)"
  cmd: uv run --no-project --python 3.10 --with numpy==2.2.6 --with psutil==7.2.2 --with sqlite-vec==0.1.9 --with usearch==2.26.5 --with threadpoolctl python src/benchmarks/vector_storage_v2.py {{.CLI_ARGS}}
```

`--no-project` matters: a plain `uv run` first installs the whole project (torch through
sentence-transformers, llama-cpp), several GB this laptop does not have room for (found 6 Nov).

Options: `--sources random,real,varied`, `--sizes 1k,5k,20k,50k,100k,300k`, `--methods …`, `--runs 5`,
`--out docs/results/vectors/`. sqlite-vec and usearch are fetched per run with `--with`, as v1 already
does, so they are not added to the project's dependencies (licences: sqlite-vec MIT / Apache-2.0,
usearch Apache-2.0, threadpoolctl BSD-3).

If go-task is not installed, run the `cmd` line directly with the options after the script name.

## Time and disk budget (estimates, to be replaced by measured times)

| Part | Estimate on this laptop | Basis |
|---|---|---|
| numpy methods, all sizes, S1 + S2 | minutes | 4.5 ms per query at 20k measured; ~15× that at 300k |
| Python loop, 1k–5k (20k) | ~1–10 min per size | about 30 µs per vector in pure Python (estimate) |
| sqlite-vec, up to 300k | ~1 min per size | v1: 31 ms at 20k on a faster laptop |
| usearch build at 300k, setting c32 / ef1024 | ~10+ min per source | 35 s at 20k measured, grows a little faster than n |
| **S3 embedding** | **unknown**: measure 500 frames first | MobileCLIP-S2 on this CPU not timed yet |
| Disk during the run | up to ~3 GB of temporary files at 300k, deleted after each size | BLOB file 1.2 GB + sqlite-vec 0.6 GB + index ~0.7 GB |

Runs are done plugged in and with the laptop otherwise idle, both written in `note`.
