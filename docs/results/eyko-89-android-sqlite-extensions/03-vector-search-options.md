# 3 · If brute force stops being enough (supervisor question B7)

> **Brute force won't scale. What is your plan past the limit?**

## First: which limit comes first? (new measurements, 4 Nov)

Since the card was written, the lead measured a faster search loop and all three tables
together on both phones (`docs/results/vectors/*-2026-11-04-*.csv`, real vectors). These
results change the question:

| In-memory search, median ms | 20k | 50k | 100k |
|---|---|---|---|
| Pixel, old loop (`blob_memory_dot`) | 37.5 | 101.6 | 254.1 |
| Pixel, **fast loop** (`blob_memory_fast`) | **7.9** | **19.6** | **39.1** |
| A32, old loop | 82.2 | 245.3 | 538.8 |
| A32, **fast loop** | **18.6** | **45.7** | **91.0** |

The fast loop returned the same top-20 as the app's loop in 400 of 400 checks at every size.

| Holding all three tables (image 512 + text 384 + audio 512 floats per row) | 20k | 50k | 100k |
|---|---|---|---|
| Pixel | 3 of 3 loaded, PSS 164 MB | **OutOfMemoryError** loading `audio_vec` | **OOM** loading `text_vec` |
| A32 | 3 of 3 loaded, PSS 160 MB | **OOM** | **OOM** |

(The Java heap growth limit is 256 MB on both phones.)

**Reading.** With the fast loop, speed stays under 100 ms up to 100k vectors even on the A32.
The **Java heap** fails first: three float32 tables do not fit at 50k rows. At 13.4 kept frames
per minute and one hour of video a day, that is about 804 rows a day, so roughly 2 months
before the out-of-memory error. That estimate assumes one audio vector per kept frame, as in
the lead's test.

So the B7 answer has two parts. **First move the vectors off the Java heap and make them
smaller. An approximate index is only needed beyond that.**

## The options

| Option | Exact? | Where vectors live | Licence | Android support | Size | Verdict |
|---|---|---|---|---|---|---|
| **O1. Off-heap float32 / f16 / int8, same brute force** (no new library) | Exact for f32; near-exact for f16 / int8 | Direct `ByteBuffer` or memory-mapped file, not the Java heap | — | Plain Kotlin / JNI | 0 | **First step** (lead's area, EYKO-100 follow-up) |
| O2. sqlite-vec `vec0` float32 | Exact (brute force) | SQLite pages on disk, read through the page cache | MIT / Apache-2.0 | Via R1 / R2 / R3 | ~150 KB `.so` | Fixes memory, not speed (scalar on Android) |
| O3. sqlite-vec int8 / bit | Exact over the quantised values; recall < 1 against float | same | same | same | same | 4× / 32× smaller; needs a float rerank |
| **O4. usearch** (HNSW) | Approximate; `exact=True` brute-force mode too | Can **view** an index from disk without loading it (memory-mapped) | Apache-2.0 | Official Android arm64 / arm32 builds (v2.26.6, 25 Oct 2026) + Java binding | `libusearch_c.so` 2.8 MB (arm64) | **Fallback index to test on the laptop** |
| O5. hnswlib | Approximate | In RAM | Apache-2.0 | None official: header-only C++, so our own JNI | small | Laptop reference only |
| O6. FAISS | Both | In RAM (or mmap for some index types) | MIT | **No official Android package**; needs BLAS + OpenMP | large (README compares ~10 MB vs usearch < 1 MB) | Overkill under 1M vectors |
| O7. ObjectBox vector search | Approximate (HNSW) | Its own on-disk DB with caching | Java binding Apache-2.0; the native core's licence was not found in the docs | Java / Kotlin | +2.3 MB per ABI download (FAQ) | Replaces SQLite: conflicts with the raw-SQL decision |

### O1 · Off-heap and smaller vectors, no new library
- **Preferable:** It fixes the measured wall (the heap OOM) directly and keeps exact search.
  It needs no SQLite change and adds nothing to the APK. f16 halves memory, and int8 cuts it to
  a quarter (one table of 50k × 512 int8 is 25.6 MB). Cosine on unit vectors survives int8
  well. Recall must still be measured (EYKO-91).
- **Not preferable:** Still linear time, though at 91 ms for 100k on the A32 that is a long way
  off. Off-heap memory is not counted against the 256 MB heap, but it is still RAM the phone
  can kill the app over, so it must show up in PSS (EYKO-95).

### O2 / O3 · sqlite-vec (needs R1 / R2 / R3 from file 02)
- **Preferable:** The data stays in SQLite, so it uses the same file, transactions and
  `link` checks. Memory is bounded by SQLite's page cache, not by table size. On the laptop
  the file was half the BLOB size (42.5 vs 82.1 MB at 20k). int8 and bit columns are built in.
  Same tables on laptop and phone, as the parity rule requires.
- **Not preferable:** It is still brute force. The Android prebuilt runs **scalar code (no
  NEON)**, so it may be slower than the fast Kotlin loop. The laptop already showed sqlite-vec
  is not fast: 31 ms against numpy's 1.5 ms at 20k. The prebuilt is also 4 KB-aligned (file
  02, R5), and it needs a SQLite migration first.

### O4 · usearch
- **Preferable:** It is sub-linear, so it is the real answer for 300k and beyond. It
  **memory-maps** an index from disk instead of loading it, which addresses the heap wall too.
  It supports i8, f16 and bf16. Official Android arm64 builds exist, and a Java binding. It is
  pip-installable, so the laptop test (EYKO-91) is quick. It has an exact mode, so one library
  covers both.
- **Not preferable:** It is approximate, so recall < 1 and must pass the pre-set mark
  (recall@20 ≥ 0.95). The index is a second store next to SQLite, so it must be kept in step
  (insert and delete) and checked by the `link` stage. Its prebuilt Android `.so` is also
  **4 KB-aligned** (`readelf`: `0x1000`; [evidence](evidence/prebuilt-so-alignment.txt)) and
  would need rebuilding with NDK r28. Java is installed from a "fat JAR", not Maven Central.

### O5 hnswlib, O6 FAISS, O7 ObjectBox: why not
- **hnswlib:** a good algorithm, but no Android or Java build, and no memory-mapped view. It
  is worth using only as a second laptop reference.
- **FAISS:** no official Android package, and it needs BLAS and OpenMP. Its strengths (IVF,
  PQ, GPU) matter at millions of vectors, not at our 10⁴–10⁵.
- **ObjectBox:** it would replace SQLite as the store, which reverses the raw-SQL and parity
  decisions from Head 2. Its core licence is not stated in the docs we read.

## B7 answer for the defence

> The limit we hit first on a phone is memory, not speed. With the improved loop, 100,000
> vectors search in 39 ms on the Pixel and 91 ms on the A32, but three float32 tables run out
> of Java heap at 50,000 rows. The plan has three steps, each with a fixed pass mark:
> (1) move vectors off the Java heap and store them as int8 or f16, keeping exact search;
> (2) if a bundled SQLite is adopted, measure sqlite-vec for memory and file size;
> (3) when a store passes about 200k vectors, or exact search passes 200 ms, use usearch.
> usearch is an HNSW index that memory-maps from disk, and it is tested on the laptop first
> for recall@20 ≥ 0.95.
