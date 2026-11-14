# 4 · The libraries, checked on this laptop

The docs left gaps, so each library was run once on this laptop before being planned in, the
same way EYKO-89 checked the Android `.so` files with `readelf`. Scripts and raw output:
[evidence/](evidence/). Every run: `uv run --no-project --python 3.10 --with <libs> python -I <script>`.

## sqlite-vec 0.1.9 (with SQLite 3.37.2 and numpy 2.2.6, the same versions v1 used)

| Question | Answer | How we know |
|---|---|---|
| int8 columns? | Yes: `vec0(e int8[512])` | probe: `ok create virtual table … int8[8]` |
| Cosine instead of L2? | Yes: `float[512] distance_metric=cosine`, also for int8 | probe |
| How to make int8 from float32 | **`vec_quantize_int8(v, 'unit')`**. The API reference names it `vec_quantize_i8` and gives it no description ("x", "todo"); that name gives `no such function: vec_quantize_i8` | probe + API reference page |
| What `'unit'` does | Treats −1…1 as the full range, which is **coarse for 512-d unit vectors**: random vectors use only **47 of 256** int8 values (−23…26), our real ones 95 (−59…53). A typical number lands on 0…5 | probe |
| Is float32 KNN exact? | Yes. A first check showed recall 0.95; 200 queries traced it to a **tie between two identical vectors** (score gap 0.0). With ties counted, it is 1.0 | `probe_sqlite_vec_ties.py` |
| Bit vectors | `bit[512]` + `vec_quantize_binary` work (sign of each number) | probe |

**What follows for the plan**
- Method `sqlite_vec_int8` uses `vec_quantize_int8(…, 'unit')` exactly as the library offers it, so
  we measure what a user of sqlite-vec would get.
- A second int8 method in numpy uses **one scale per vector** (largest |number| → 127), so all 256
  levels are used. It shows how much of any int8 loss is the `'unit'` choice and how much is int8
  itself. EYKO-109 (int8 on the phone) needs exactly that answer.
- The recall rule must **count ties** (see [02](02-benchmark-design.md)).

## usearch 2.26.5 (Python package; the Android build in EYKO-89 was 2.26.6)

| Question | Answer | How we know |
|---|---|---|
| API | `Index(ndim, metric="cos", dtype="f32"/"f16"/"i8", connectivity=16, expansion_add=128, expansion_search=64)`; `add(keys, vectors, threads=)`; `search(q, 20, exact=, threads=)` → `.keys`, `.distances`; `save` / `load` / `view` (from disk without loading) | README + probe |
| Default recall on random 20k | **0.20–0.25** (f32, f16, i8) | probe |
| Recall after tuning | connectivity 16 / ef 256: 0.600 (2.1 ms); 16 / 1024: 0.945 (6.1 ms); **32 / 1024: 0.997 (8.3 ms)**; 32 / 4096: 1.000 (13.5 ms); one search thread | probe |
| `exact=True` | Brute force inside usearch: f32 **1.000** (2.07 ms), f16 1.000 (1.01 ms), **i8 0.830** (0.47 ms) | probe |
| Memory | index of 20k: f32 67.4 MB, f16 / i8 33.8 MB (`memory_usage`) | probe |

**What follows for the plan**
- usearch runs as a **small grid**, not one setting: (connectivity, expansion_search) ∈
  {(16, 64), (16, 256), (32, 1024)}. The CSV says which. Build time and index size are reported
  separately from query time.
- Its search uses **`threads=1`**, the fair comparison with the one-thread phone loop. Build uses
  all threads, since it happens once.
- `exact=True` is a useful extra row: a SIMD brute force in C++. It shows how far a fast native
  loop could take exact search on one core (B5).
- **i8 in usearch lost recall even in exact mode (0.83) on random data.** S3 will show whether
  that holds on real data.

## hnswlib

**No prebuilt package for Python 3.10 on Linux.** `uv --no-build` says the requirements are
"unsatisfiable", and building from source hung, so the probe was stopped. EYKO-89 had already put it
as "laptop reference only". **Dropped from the plan**; usearch covers HNSW.

## numpy 2.2.6 (OpenBLAS)

- `m @ q` uses OpenBLAS threads by default. The plan reports **two numpy rows**: default threads,
  and one thread through `threadpoolctl` (`uv run --with threadpoolctl`). The one-thread row is the
  fair comparison with the phone (B5).
- Ranking uses `argpartition` + sorting only the top 20, the honest best case. v1 used a full
  `argsort`, so v1 and v2 numpy times are not the same method.

## psutil 7.2.2 on Linux

`Process().memory_full_info()` gives **PSS** (and USS) on Linux, and `resource.getrusage(...).ru_maxrss`
gives the peak in KB. So the laptop's `pss_mb` can be real PSS, the same measure the phones report,
instead of the card's "peak RSS".
