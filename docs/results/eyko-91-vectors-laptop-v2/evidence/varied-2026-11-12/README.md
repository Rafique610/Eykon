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
