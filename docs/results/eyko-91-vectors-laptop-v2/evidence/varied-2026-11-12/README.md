# EYKO-91 step 5 · S3 varied run, 12 November 2026

**What ran:** `vector_storage_v2.py --sources varied --sizes 1k,5k,20k,50k,100k` (5 runs)
at commit `fe17d8d` (clean tree), laptop i5-10310U **plugged in** (`charger=in` in every row),
about 5 min, exit 0. The DB-read and Python-loop methods stop at 20k.

**Vectors:** the first 100,000 COCO train2017 photos by id, embedded with MobileCLIP-S2
(datacompdr) by `embed_coco.py`; queries are the first caption of 21 val2017 photos (seed 90).
All 100,000 rows checked: unique ids, max |norm − 1| = 1.8e-7. The vectors stay in
`data/eyko91_coco/` (git-ignored).

| File | Contents |
|---|---|
| [`../../../vectors/laptop-2026-11-12-sweep-varied.csv`](../../../vectors/laptop-2026-11-12-sweep-varied.csv) | S3 varied: 305 rows (61 method × size groups × 5 runs) |
| `run-log.txt` | the script's console output |
| `1-time-vs-size.png` | median time per search against size, S1 · S2 · S3 side by side |
| `2-recall-vs-size.png` | recall@20 against size for the approximate methods, 0.95 pass mark, S1 · S2 · S3 |
| `3-memory-vs-size.png` | memory held (PSS after − before) against size, S3 |
| `4-phone-vs-laptop.png` | B5: the phones' search (A32 cable, A32 hot, Pixel, A32 before EYKO-114/115) against one-thread numpy, S2, 20k–100k |
| `hnsw-rebuilds.txt` | each HNSW setting built 5 more times at 100k (`vector_storage_v2.py --one varied 100000 <method> --runs 1`, 12–13 Nov): recall moves by ≤ 0.005 |
| `graphs.py` | draws the four charts (a quick look; the official figures are EYKO-97) |

Redraw: `uv run --no-project --python 3.10 --with matplotlib python -I <this folder>/graphs.py docs/results/vectors <out dir>`

**What S3 shows:** on 100,000 distinct real photos, HNSW keeps its recall far better than on S1
(random) or S2 (near-copies): c16/ef64 0.95, c16/ef256 0.98, c32/ef1024 1.00 at 100k, at
0.3–3 ms against 12.9 ms for numpy. int8 + re-check stays at 1.00; sqlite-vec int8 falls to 0.84.
