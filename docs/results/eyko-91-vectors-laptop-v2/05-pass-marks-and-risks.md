# 5 · Pass marks (fixed before running) and how the numbers could lie

`core.md` and the lead's 4 Nov rule ("no decision without evidence") ask for the bar to be set
**before** any result is read. These are proposals until the lead confirms them on the card.

## Pass marks

| What | Mark | Source of the mark |
|---|---|---|
| Exact methods (1, 2, 3, 4, 8, 13) | recall@20 = **1.0** (ties counted) at every size and source. Lower = a bug; stop and fix before any timing is reported | card |
| Approximate index (usearch rows 10–12) | worth porting only if **recall@20 ≥ 0.95 and ≥ 5× faster** than in-memory BLOB search | card |
| … judged on which data | **S3 (varied real), at its largest size** (target 100k), not random. Random has no neighbourhoods: defaults gave 0.20–0.25 and 0.997 cost more time than brute force ([04](04-libraries.md)) | **proposed change**: the card says "at 300k" |
| … "in-memory BLOB" means | `blob_memory_numpy_1t` (one thread, the fair comparison with the one-thread phone loop). The multi-thread row is reported next to it | proposed: the card does not say |
| float16 / int8 (rows 5–7, 9) | **recall@20 ≥ 0.99** on S3, the same mark EYKO-109 sets for the phone. Below that the method is listed, not proposed | EYKO-109 |

Nothing in this card "adopts" a method for the app. It produces the laptop evidence, and EYKO-98 (the
lead's storage decision) decides.

## How these numbers could lie (to be written into the result file, with numbers)

1. **One laptop, not the v1 laptop.** A 4-core i5 against v1's 12 threads. Only same-machine
   comparisons are fair; laptop-to-phone ratios depend on which laptop.
2. **Multi-thread numpy flatters the laptop.** The phone loop is single-threaded, so for B5 the
   `_1t` row is the one to quote.
3. **The phone's "real" set (S2) is 90 vectors + noise.** Fine for time, not for recall
   ([03](03-vector-sources.md)). Its noise is drawn by numpy, not by Java's `Random`, so it matches the
   phones in kind, not bit for bit.
4. **S3 is not our users' data.** It is first-person video embedded with our model, but kitchens are
   not a user's whole day. Recall on our own clips could differ.
5. **S3 stops short of 300k.** The index's recall at 300k is extrapolated from the largest S3 size.
   Say so next to the number.
6. **Index build time and memory are left out of query time.** An HNSW index costs minutes to build at
   300k and extra memory for the graph. Both are reported separately, and the verdict must weigh them.
7. **Python and numpy versions.** Python 3.10.12, numpy 2.2.6, SQLite 3.37.2 (the same as v1), sqlite-vec
   0.1.9, usearch 2.26.5 (the Android build is 2.26.6). Written into every result file.
8. **Thermal state.** A laptop slows when hot; CPU temperature is logged at the start and end of each
   row, and the run is done plugged in.
9. **Warm caches.** Every query after the warm-up finds the data in memory or the OS cache, the best
   case. The first-search cost on the phone (about 1 s, Head 7) is not modelled here.
10. **numpy's float16 is slow, not float16 itself.** In the 6 Nov self-check at 1k, `blob_memory_f16`
    took 2.2 ms against 0.04 ms for float32: numpy widens float16 to float32 in software. So its
    laptop time says little about a phone loop; its recall and memory are what count here.
11. **An HNSW index built on several threads is not repeatable.** Three builds of the same 5k random
    set gave recall@20 0.535, 0.55 and 0.4875 (c16 / ef64); one-thread builds gave 0.56 every time.
    Builds stay multi-threaded (one thread would be ~4× slower at 300k), so the write-up reports the
    spread over several builds before quoting a recall against the 0.95 mark.
12. **Charger.** The 7 Nov smoke run was on battery (`charger=out` in its rows), and times moved
    between runs (int8 at 5k: 1.2 and 3.0 ms). Steps 4–5 run plugged in, and rows with
    `charger=out` are not used for timing.

## Things noticed while planning (flagged, not acted on)

1. **Ego4D access ended on 1 Nov 2026**, and the Pixel `memories.db` holds Ego4D vectors. The card's
   step 5 should be amended: own-clip vectors only ([03](03-vector-sources.md)).
2. **The committed own-clip vectors contain exact duplicates**: 5 identical pairs in
   `own_image_512.f32` and 9 in `own_text_384.f32`. Identical frame vectors should not survive the
   dedup stage, which drops anything at cosine ≥ 0.95. A likely cause is the same clip imported twice,
   gap **EYKO-71** ("same file can be added twice"). The lead should check which frames these are.
   (Identical text vectors are expected: same caption, same vector.)
3. **The sqlite-vec API reference has the wrong name** for its int8 function (`vec_quantize_i8`; the
   real one is `vec_quantize_int8`). Worth knowing for EYKO-104 to 108, which use sqlite-vec on the phone.
4. **sqlite-vec's `'unit'` int8 uses only 47–95 of 256 levels** on 512-d unit vectors. The phone route
   cards (EYKO-105 to 108) should report int8 recall, not assume it.
5. **`task` (go-task) is not installed on this laptop**, and v1's peak-memory line is Windows-only.
