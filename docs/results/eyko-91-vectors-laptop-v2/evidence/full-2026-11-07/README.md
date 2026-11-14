# EYKO-91 step 4 · full run, 7 November 2026

**What ran:** `vector_storage_v2.py --sources random,real --sizes 1k,5k,20k,50k,100k,300k --runs 5`
at commit `243bd98` (clean tree), laptop i5-10310U **plugged in** (`charger=in` in every row),
about 1 h 45 min, exit 0. The DB-read and Python-loop methods stop at 20k.

| File | Contents |
|---|---|
| [`../../../vectors/laptop-2026-11-07-sweep.csv`](../../../vectors/laptop-2026-11-07-sweep.csv) | S1 random: 360 rows (72 method × size groups × 5 runs) |
| [`../../../vectors/laptop-2026-11-07-sweep-real.csv`](../../../vectors/laptop-2026-11-07-sweep-real.csv) | S2 phone-real: 360 rows |
| `run-log.txt` | the script's console output |
| `1-time-vs-size.png` | median time per search against size, both sources |
| `2-recall-vs-size.png` | recall@20 against size for the approximate methods, 0.95 pass mark |
| `3-memory-vs-size.png` | memory held (PSS after − before) against size, random |
| `full_graphs.py` | draws the three charts (a quick look; the official figures are EYKO-97) |

Redraw: `uv run --no-project --python 3.10 --with matplotlib python -I <this folder>/full_graphs.py docs/results/vectors <out dir>`

## Checks

| Check | Result |
|---|---|
| Every exact method gives recall@20 = 1.0 at every size, both sources | ✅ (the script stops otherwise) |
| 5 rows per (method, size), one commit, no `-dirty`, charger in | ✅ 720 rows, `243bd98` |
| Heat | only `blob_memory_numpy` (8 threads) reached 85–91 °C, at 50k and above |

## Seen

- At 300k: one-thread numpy 36–39 ms (634 MB); int8 + re-check 72 ms, recall 1.0 (199 MB);
  float16 ~285 ms (numpy's float16 is slow, risk 10); sqlite-vec f32 ~370 ms; sqlite-vec int8
  recall 0.65–0.81.
- HNSW stays fast (1–23 ms) but its recall falls with size on both sources (best setting 0.57 on
  random, 0.08 on phone-real at 300k). S2 has ~3,300 near-identical copies per clip at 300k, the
  worst case for HNSW, as random vectors are; the HNSW verdict waits for S3 (step 5).
- The HNSW c32/ef1024 build on random 300k took 23 minutes.
