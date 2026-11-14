# EYKO-91 step 3 · smoke run, 7 November 2026

**What ran:** `vector_storage_v2.py --sources random --sizes 1k,5k --runs 5` at commit `9b70fd2`
(clean tree). 13 methods × 2 sizes × 5 runs × 20 timed queries = **130 CSV rows**, 46 s.
Laptop i5-10310U, Python 3.10.12, numpy 2.2.6, SQLite 3.37.2, sqlite-vec 0.1.9, usearch 2.26.5.

**This is a check that the benchmark works, not a result.** The laptop was **on battery**
(`charger=out` in every row), so the times are not used anywhere. Steps 4–5 run plugged in.

| File | Contents |
|---|---|
| `laptop-2026-11-07-sweep.csv` | the 130 rows, shared phone format + `recall_at_20` |
| `run-log.txt` | the script's console output (median of the 5 run medians per method) |
| `tests.txt` | `tests/test_vector_recall.py`: 8 passed |

## Checks

| Check | Result |
|---|---|
| Every method runs at 1k and 5k without an error | ✅ 26 of 26 |
| Exact methods (`blob_disk_dot`, `blob_memory_numpy`, `_1t`, `_pyloop`, `sqlite_vec_f32`, `usearch_exact_f32`) give recall@20 = 1.0 | ✅ all 6, both sizes, every run (the script stops otherwise) |
| 5 rows per (size, method), every row has the same commit, no `-dirty` | ✅ 130 rows, `9b70fd2` |
| int8 + re-check is slower than int8 alone (it does the same work and more) | ✅ 3.00 vs 2.15 ms at 5k |
| Memory: int8 / float16 hold less than float32 once the scratch buffer is counted | ✅ (int8 35 MB incl. 8 MB `scratch_mb`; float32 34 MB) |

## Found and fixed during this step (all in `9b70fd2`)

1. **Freed memory still counted.** glibc keeps freed pages, so a method that makes copies while
   building looked bigger than it is (int8 at 5k: 42.7 MB, really 25.6 MB). The child process now
   calls `malloc_trim(0)` before reading PSS.
2. **Every method used all 8 BLAS threads**, not just the multi-thread reference. At 5k, numpy took
   5.9–8.9 ms with 8 threads against 0.6 ms with one, and int8 got slower each run (1.8 → 8.8 ms).
   Every method but `blob_memory_numpy` now runs BLAS on one thread, like the phone loop
   (`blas_threads` in `note`).
3. **float16 / int8 allocated a new array on every query**, so their times swung (1.5–5.6 ms at
   5k). They now reuse one scratch buffer, recorded as `scratch_mb`.

## Seen, not changed

- **An HNSW index built on all threads is not repeatable:** three builds at 5k gave recall 0.535,
  0.55 and 0.4875 (one-thread builds: 0.56 each time). Builds stay multi-threaded, and the
  write-up will report the spread ([05](../../05-pass-marks-and-risks.md), item 11).
- **Multi-thread numpy is noisy at small sizes** (1k: 0.05 ms in one run, 3.10 ms in another):
  waking 8 threads costs more than the work. The one-thread row is the one to compare (B5).
- **HNSW on random vectors** finds only 0.52 of the true top 20 at 5k with the default setting,
  as the planning probe predicted. Random vectors are its worst case; the verdict waits for S3.
