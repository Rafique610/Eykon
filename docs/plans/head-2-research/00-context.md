# Head 2 research: project context (Taha's cards)

Written 4 November 2026 from the Synverk board (project Eykon, flows Head 1 to 8 and the
complete map) and the repo on `feature/video-memory` at `7fc6af7`. The cards are the plan;
where this file and a card disagree, the card wins.

My cards: [EYKO-89](01-eyko-89-android-sqlite-extensions.md),
[EYKO-91](02-eyko-91-laptop-vector-benchmark-v2.md),
[EYKO-97](03-eyko-97-graphs-and-capacity-model.md).

## What Eykon is

A second brain that lives on the phone. You record video, the phone works out what is in
each moment, and later you ask "where are my keys?" and get back the frame, the time and the
place, as proof. Nothing leaves the device. The laptop is the lab, where models are picked,
exported to ONNX and checked against golden frames. The phone, in Kotlin, is the product.

## The pipeline, one head at a time

| Head | What it does | How it works |
|---|---|---|
| 1 Project start | Text memory first, then video | Phase 1: notes in raw sqlite3, bge-small 384-d, BM25 + dense fused with RRF (k = 60), cross-encoder rerank (Hit@1 76.7 %). Phase 2: Kotlin + Compose, Room, Gemma 4 E2B on LiteRT-LM. Phase 3: a VLM captioning every frame took about 13 s a frame and 4.68 W, so the project moved to cheap specialised models (Option A). |
| 2 Setup & storage | Where vectors live, and the ground rules | sqlite-vec did not load on Android, so vectors are float32 BLOBs in plain tables, loaded into memory once and searched by dot product. Raw SQL with no ORM. The laptop and phone keep identical schemas and models. Tests use pytest and on-device tests, tooling is uv + Taskfile. |
| 3 Video intake | Clip in, job queued | The picker copies the file into app storage and reads time, duration and GPS. One worker runs 10 stages in order and saves the stage after each one, so a crash resumes there. A job fails after 3 attempts and can be retried. |
| 4 Processing | About 225 frames down to 10–16 | Split at 3 fps, 640 px. Plain-maths filters drop dark, bright, blurry and still frames. The sharpest frame per 3 s slot is kept. Repeats are removed with dHash (≤ 6 bits) and then MobileCLIP-S2 cosine ≥ 0.95. |
| 5 Scene | What is in each kept frame | YOLOX-Tiny (COCO 80) + D-FINE S (Objects365), merged. MobileCLIP picks the place and the action by phrase. A MobileCLIP gate decides when to run YOLOE-11L for keys and earbuds. One caption per frame goes into `scene_records`. |
| 6 Indexing | Make it searchable | The 512-d MobileCLIP frame vector goes to `image_vec`. The caption goes to FTS4 plus a bge-small 384-d vector in `text_vec`. A link check (10 counts must be zero) fails the job rather than repairing anything. "Latest" groups objects by crop cosine ≥ 0.87. |
| 7 Search | Typed phrase → result card | The MobileCLIP text encoder makes a 512-d vector, which is scored by cosine against **every** `image_vec` row held in memory. Each hit grows into a time window and the best 20 are returned. This step is the one Head 2's storage decision has to keep fast. |
| 8 Evaluation | Ego4D scores | Set A (24 clips) for tuning, set B held out. Pixel run: 372 frames kept in 27.8 min of video, so **13.4 kept frames per minute**. Phone and laptop agree on 354 of 372 seconds. |

Coming: Ask & answer (9), speech and sound with an `audio_vec` table (10), tuning (11), the
phone gate and defence (12).

## The crux of Head 2

Search in Head 7 is **exact brute force**. Every query computes a dot product against every
stored frame vector, so search time grows linearly with how much video the user has ever
recorded. The 12 October decision (EYKO-31) was correct for the first weeks of use. Head 2's
open work is to show, with numbers a strict examiner accepts, three things:

1. **Why** sqlite-vec failed: is it Android or sqlite-vec? (A2, A3, EYKO-89)
2. **That BLOB search is right**, not just fast. Recall must equal exact search (A5, EYKO-91).
3. **When it stops being good enough**, and what replaces it then (B2, B7, EYKO-91, EYKO-97).

### How vector search runs on the phone today

`android/.../video/VideoVectors.kt`:

- Vectors are stored as little-endian float32 BLOBs, `INSERT OR REPLACE` into `image_vec(frame_id, embedding)`.
- On the first `knn` call the whole table is read into one Java `FloatArray` (rows × 512) and
  cached, keyed on `(COUNT(*), MAX(id))`. Any `put` drops the cache.
- Each query runs a plain Kotlin double loop to compute the dot products, then
  `scores.indices.sortedByDescending { … }.take(k)`. That is a **full sort of boxed Integers**,
  not a top-k selection.
- `VideoSearch.frames` calls `knn(..., k = Int.MAX_VALUE)`, so every score is sorted on
  every search.

### What has already been measured (3 Nov sweep, `docs/results/vectors/`)

In-memory search, median ms per query, 512-d, random vectors:

| n | Pixel 9 Pro XL | Samsung A32 |
|---|---|---|
| 1k | 1.6 | 3.3 |
| 5k | 8.7 | 16.9 |
| 20k | 40.4 | 80.5 |
| 50k | 108.6 | 252.6 |
| 100k | ~270 | 534.6 |
| 300k | **OutOfMemoryError** (614 MB array, 256 MB heap limit) | not run |

Two things follow that the cards do not yet state:

- **The 200 ms line is already crossed** at about 41k vectors on the A32 and about 78k on the
  Pixel (linear interpolation between the measured sizes).
- **The memory wall comes before the speed wall at large sizes.** A float32 512-d vector is
  2 KB. The Pixel's 256 MB heap growth limit therefore caps one table at roughly 120k vectors,
  and less once the reload copy is counted. The capacity model (EYKO-97) has to report both
  limits.

## Running list of things noticed (to flag, not fixed)

1. The committed sweep CSVs have an extra trailing `note` column that the card's shared
   format does not list. Either the format or the CSVs should change. Plotting code should
   accept both.
2. The Pixel sweep heated from 33.2 °C to 38.1 °C while charging, so it is not a clean
   baseline (already noted for B8, but it also affects the in-memory numbers).
3. Full sort plus `Int.MAX_VALUE` in production search: part of the "phone is 50× slower"
   (B5) is this sort, not the chip. It is measured inside both the spike and the app.
4. EYKO-91 calls sqlite-vec int8 an "exact method that must have recall 1.0". Quantised
   search is exact over int8 numbers, not over the original floats, so its recall can drop
   below 1.0. The pass mark should list it with the approximate methods.
5. EYKO-97's formula multiplies vectors per day by "tables". A search scans **one** table
   (`image_vec`), so time depends on the per-table count. Memory depends on the sum across
   tables. The model should keep the two separate.
6. `src/benchmarks/vector_storage_spike.py` reads `peak_wset`, which exists only on Windows.
   On Linux it prints current RSS, not peak RSS.
7. `matplotlib` is not a project dependency. Use `uv run --with matplotlib` in the Taskfile,
   as the sqlite-vec spike already does, unless the lead wants it added to dev dependencies.
