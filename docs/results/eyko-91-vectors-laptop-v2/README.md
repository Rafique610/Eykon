# EYKO-91 · Laptop vector benchmark v2: plan

Card EYKO-91 (Head 2), planned 5 November 2026 by Taha Ahmed. Branch
`taha/eyko-91-vectors-laptop-v2` from `origin/feature/video-memory` @ 972091d.
Answers, once run: **A5** (same results or just faster?), **B1** (spread), **B2** (sizes), **B3**
(real data), **B5** (chip or code), **B7** (plan past brute force), and the laptop half of
**EYKO-109** (float16 / int8).

**Status: steps 1–4 done** (sources + recall tests, 13 methods + runner, smoke run on 7 Nov:
[evidence/smoke-2026-11-07](evidence/smoke-2026-11-07/README.md); full run on S1 + S2, 1k–300k,
plugged in, 7 Nov: [`laptop-2026-11-07-sweep.csv`](../vectors/laptop-2026-11-07-sweep.csv),
[`-sweep-real.csv`](../vectors/laptop-2026-11-07-sweep-real.csv),
[run log](evidence/full-2026-11-07/run-log.txt)). The owner decided D1 and D2 on 6 Nov; D3 (pass
marks) was decided on 7 Nov, **after** the full run. The marks change the verdict, not the data.

## The plan in one paragraph

A new script, `vector_storage_v2.py` (v1 stays as it is), times **13 methods** at **1k–300k** vectors
with 1 warm-up and 5 runs × 20 queries. The methods: BLOBs from disk; numpy with all threads and with
one thread; a plain Python loop; numpy float16 and int8; sqlite-vec float32 and int8; usearch at three
settings and in its exact mode. Every method is checked for **recall@20 against exact search, with
ties counted**, and measured for **PSS** in a fresh process each. The runs use **three kinds of
vectors**: random (comparable with v1 and the 3 Nov phone sweep), the phones' own 90 real + noise
(comparable with the 4 Nov phone sweep), and a **varied real set** embedded with our MobileCLIP-S2
model, which is the only fair test of int8, float16 and the approximate index. Results go into the
shared CSV that EYKO-97's graphs read.

## What the planning found (checked on this laptop, not just read)

1. **Random vectors are useless for judging an approximate index.** usearch at default settings found
   **20–25 %** of the true top 20 on random 20k. Reaching 0.997 made it **slower than numpy brute
   force** (8.3 ms against 4.5 ms). So the card's pass mark has to be judged on varied real vectors.
   → [04](04-libraries.md)
2. **sqlite-vec's int8 function is misnamed in its own docs** (`vec_quantize_i8` does not exist; the real
   name is `vec_quantize_int8`). Its `'unit'` mode uses only **47–95 of 256** int8 levels on our vectors.
   → [04](04-libraries.md)
3. **The committed own-clip vectors contain exact duplicates** (5 identical image pairs, 9 text pairs).
   A recall check without tie handling reports false misses. Identical frame vectors also hint that the
   same clip was imported twice (gap EYKO-71). → [05](05-pass-marks-and-risks.md)
4. **Ego4D access ended on 1 Nov 2026**, and the Pixel database the card points to holds Ego4D vectors.
   The plan uses own-clip vectors only. → [03](03-vector-sources.md)
5. **This is a different laptop from v1** (4-core i5 against the lead's 12 threads) with **15 GB of free
   disk**. Every v1 method is rerun here, and any real dataset is streamed. → [01](01-what-v1-measured-and-what-is-missing.md)
6. **hnswlib has no prebuilt package** for Python 3.10 on Linux, so it is dropped (usearch covers HNSW).

## Decisions

| # | Question | Decision |
|---|---|---|
| D1 | Varied real vectors (S3): which source? | **EPIC-KITCHENS slice** (decided by the owner, 6 Nov 2026): about 30 videos streamed one by one, frames every 2 s, MobileCLIP-S2 vectors, narrations as text queries, target 100k vectors. COCO stays the fallback if downloads are too slow |
| D2 | CSV file name | **One file per source** (decided by the owner, 6 Nov 2026): `laptop-<date>-sweep.csv` (random, the same suffix as the phones' random sweep), `-sweep-real.csv`, `-sweep-varied.csv`, named like the phone files so EYKO-97's graphs pick the laptop up. This differs from the card's single `laptop-<date>.csv`; the card comment will say so |
| D3 | Pass marks (for the lead, on the card) | **Decided 7 Nov 2026** by the lead (Taha Ahmed), agreed by the reviewer (Rafique, EYKO-91 comment, 15:41 UTC): (1) the index is judged on S3 (varied real, EPIC-KITCHENS) at its largest size, not on random vectors "at 300k"; (2) "in-memory BLOB" = `blob_memory_numpy_1t`, with the all-threads `blob_memory_numpy` reported next to it; (3) float16 / int8 mark recall@20 ≥ 0.99, ties counted. **The 7 Nov full run (S1 + S2, 14:44 UTC) finished before D3 was written down**; D3 changes how the rows are judged, not the rows |

## Files

| File | Contents |
|---|---|
| [01-what-v1-measured-and-what-is-missing.md](01-what-v1-measured-and-what-is-missing.md) | v1, what the phones added since, each card step against today, the machine |
| [02-benchmark-design.md](02-benchmark-design.md) | 13 methods, sizes, timing, recall with ties, memory, CSV, code layout, task, time budget |
| [03-vector-sources.md](03-vector-sources.md) | S1 random, S2 phone-real, S3 varied real; the Ego4D problem; S3 options |
| [04-libraries.md](04-libraries.md) | sqlite-vec, usearch, hnswlib, numpy, psutil, each checked on this laptop |
| [05-pass-marks-and-risks.md](05-pass-marks-and-risks.md) | marks fixed before running, how the numbers could lie, things noticed |
| [sources.md](sources.md) | sources table and what was not found |
| [evidence/](evidence/) | probe scripts and their raw output |

## Steps once the decisions are in

1. Write `_vector_sources.py` (S1, S2, recall with ties) and `tests/test_vector_recall.py`; run the tests.
2. Write `_vector_methods.py` (13 methods) and `vector_storage_v2.py`; add `task vectors-laptop-v2`.
3. Smoke run: S1 at 1k and 5k, all methods; check every exact method gives recall 1.0.
4. Full run on S1 and S2 (1k–300k) → the first two CSVs.
5. S3: export MobileCLIP-S2 (CPU build), time 500 frames, then stream and embed up to the target.
   Run the benchmark on S3 → the third CSV.
6. Write `docs/results/<date>-vectors-laptop-v2.md`: method, every number, and how they could lie.
   Update the Head 2 document (A5, B1, B3, B5, B7, E-items). PR, card comment, Review.
