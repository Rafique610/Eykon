# EYKO-91 · Laptop vector benchmark v2: recall, fallback index, shared CSV

Card: [EYKO-91](https://synverk.abdulhaque.dev/projects/bc6e8969-e244-4916-b158-2903baf02996/tasks/91).
Answers A5, B1, B2, B3, B5 (laptop half), B7. EYKO-97 is blocked until this card is done.
Branch: `taha/eyko-91-vectors-laptop-v2`.
Outputs: `src/benchmarks/vector_storage_v2.py`, task `vectors-laptop-v2`,
`docs/results/vectors/laptop-<date>.csv` and `docs/results/<date>-vectors-laptop-v2.md`.

## The gaps this closes

| Gap today (v1, `vector_storage_spike.py`) | v2 |
|---|---|
| One run, 20 queries, no spread | 1 warm-up + 20 queries × 5 runs; median, p95, worst |
| Only 5k and 20k | 1k, 5k, 20k, 50k, 100k, 300k |
| Never checked that methods return the same top 20 | Recall@20 against exact numpy |
| Random vectors only | Random + real (`image_vec` / `text_vec` from the Pixel DB) |
| numpy vs a Kotlin loop: unfair comparison | Adds a plain-Python loop to show how much of the gap is code (B5) |
| No approximate fallback | One ANN index (usearch recommended by EYKO-89) |
| `peak_wset` is Windows-only | Peak RSS measured per method in its own subprocess |

## Design of the script

Keep it under 300 lines (`core.md`). If it grows past that, split it into
`vector_storage_v2.py` (runner + CSV) and `_vector_methods.py` (one small class per method).

```
for source in (random, real):              # source_vectors column
  for n in sizes:
    vecs, queries = load(source, n)        # unit-normalised float32
    truth = exact_topk_numpy(vecs, queries, 20)      # ground truth once per (source, n)
    for method in methods:
      run in subprocess -> build/load, 1 warm-up, then 5 runs × 20 queries
        times -> median/p95/worst per run; recall@20 vs truth; file_mb; peak RSS
      append 5 rows to CSV
```

**Why a subprocess per (method, n):** peak RSS (`resource.getrusage(RUSAGE_SELF).ru_maxrss`,
KB on Linux) only ever goes up within a process, so measuring several methods in one process
gives wrong numbers. `multiprocessing` with `spawn` gives a clean process for each
measurement. The parent writes the CSV.

**Methods** (the `method` column names should match the phone CSVs where the method is the
same):

| method | How |
|---|---|
| `blob_disk_dot` | `SELECT embedding FROM image_vec` → `np.frombuffer` → `m @ q` → `argpartition` top 20, on every query. Cap at 20k as the phone does (`diskMax`) and write a `note` for skipped sizes. |
| `blob_memory_dot` | The matrix is loaded once; `m @ q` + `argpartition` |
| `blob_memory_pyloop` | Plain Python `for` loops for the dot product. Run it only at 1k / 5k (and 20k if under ~1 min), then extrapolate and say so. The point is the ratio to numpy, not the absolute time. |
| `sqlite_vec_f32` | `vec0(embedding float[512])`, `MATCH ? AND k = 20`; through `uv run --with sqlite-vec` |
| `sqlite_vec_int8` | `vec0(embedding int8[512])`. Quantise in numpy (`round(v * 127)` for unit vectors) and record the scheme. **Not exact**, see below. |
| `usearch_hnsw` (or `hnswlib_hnsw`) | Default parameters first, then one tuned row (e.g. `expansion_search` up) if recall < 0.95. Build time is reported separately and is not part of query time. |

Use `argpartition` + a sort of only the top 20, not a full `argsort`, so that the laptop's
exact method is the honest best case. Record which one was used.

## Real vectors (B3): how to get enough

The Pixel `memories.db` holds only about 400 kept-frame vectors (372 from Ego4D + own clips).
That is too few to reach 300k. The approaches:

| Approach | Gets to | Cost | Honesty |
|---|---|---|---|
| **A. Pixel DB only** | ~400 | Ask the lead for `memories.db` | Real, but sizes above ~400 cannot be "real" |
| **B. Pixel DB + every Ego4D frame, embedded on the laptop** (recommended) | Set A + B at 3 fps ≈ (177 + 194) min × 180 ≈ **67k** image vectors | Hours of laptop CPU through the existing MobileCLIP ONNX (`task ego4d-pipeline` already decodes frames). Cache to `D:\eykon-cache` / `~/eykon-cache`, never git. | Same model and distribution as the app. Note that unfiltered frames are more similar to each other than kept frames are, which makes the search harder, not easier. |
| C. Real up to ~67k, then sample with replacement + small noise up to 300k | 300k | Cheap | Synthetic above 67k: label `source_vectors = real_augmented` and say so |

**Queries.** For random sources, use random queries. For real sources, use real text queries:
MobileCLIP text vectors of the Ego4D NLQ questions and object names. A real search compares a
text vector against image vectors, and recall for ANN indexes depends heavily on that
cross-modal query distribution. Random queries against real data would overstate ANN recall.

For `text_vec` (384-d, bge-small): use caption vectors from the Pixel DB and bge-encoded NLQ
questions as queries. It is a second, smaller table, so 1k–20k is enough.

## Recall@20 and the pass mark

- recall@20 = |method top-20 ∩ exact top-20| / 20, averaged over the 20 queries.
- `blob_*` and `sqlite_vec_f32` must be 1.0. With float32 ties, compare sets of ids, not
  their order, and allow a tie at rank 20 (count it as a hit if the score equals the 20th
  score).
- **Flag for the lead:** the card lists sqlite-vec int8 among the exact methods. Quantisation
  changes the vectors, so its recall is expected to be about 0.95–0.99, not 1.0. I would
  report it under the approximate pass mark and say so in the write-up rather than call it a
  failure.
- Pass mark (fixed before running, copy it into the result file's first lines): an
  approximate index is worth porting only if **recall@20 ≥ 0.95 and it is ≥ 5× faster than
  `blob_memory_dot` at 300k**.

## CSV

Header exactly as the card gives it. The committed phone CSVs append a `note` column, so
either write `note` too (recommended, for consistency with the files already in
`docs/results/vectors/`) or ask the lead to settle the format. Laptop: `android` is empty,
`pss_mb` = peak RSS, `heap_mb` empty, and temperature and battery empty unless read from
`psutil.sensors_*`. Add **one more column, `recall_at_20`**, after `source_vectors`. EYKO-97
needs it, and the card's header has nowhere else to put it. Confirm with the lead first.

`commit` = `git rev-parse --short HEAD`, plus `-dirty` if the tree is not clean.

## Approaches to the card, compared

| Approach | Effort | Pros | Cons |
|---|---|---|---|
| **1. Extend v1 in place** | Smallest | Little code | The card says keep v1 unchanged, and v1 has no recall or subprocess isolation |
| **2. New v2 script, random vectors first, real vectors as a second pass** (recommended) | ~2 days | The CSV for EYKO-97 is out on day 1. Real vectors arrive when the DB / Ego4D embeddings are ready. Each pass is independently useful. | Two runs to describe |
| 3. Use `ann-benchmarks` | Medium | A standard harness that reviewers recognise | Does not produce the shared CSV, has no sqlite-vec BLOB baseline, and adds heavy deps |

**Time budget at 300k on the laptop.** The float32 matrix is 600 MB, and that is fine. The
usearch build at 300k × 512 takes a few minutes. `blob_disk_dot` is capped at 20k. The
Python loop runs only at small n. Expect the whole sweep to take about 30–60 minutes. Run it
on a cool, idle laptop with the charger plugged in, and record that.

## "How these numbers could lie" (prepare for the write-up)

- numpy uses BLAS with many threads. The phone code uses one thread. Also run once with
  `OMP_NUM_THREADS=1` / `OPENBLAS_NUM_THREADS=1` and report the single-thread column. This
  is the fair laptop-to-phone comparison for B5.
- Augmented real vectors above 67k are not real.
- ANN timing excludes build time and index memory. Report both separately.
- One laptop. Timings depend on turbo and thermal state.

## Done-when checklist

- [ ] `task vectors-laptop-v2` runs end to end from a clean clone (sqlite-vec / usearch
      through `uv run --with`)
- [ ] CSV committed under `docs/results/vectors/laptop-<date>.csv`
- [ ] Recall table: exact methods 1.0, int8 and ANN with their numbers
- [ ] B5 answer: numpy vs Python loop vs single-thread numpy
- [ ] Result file with the method, every number, and the limits
- [ ] Recommendation for EYKO-89's fallback index: passes or fails the pre-set mark
