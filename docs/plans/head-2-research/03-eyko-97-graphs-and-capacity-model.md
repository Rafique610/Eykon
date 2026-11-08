# EYKO-97 · The seven Head 2 graphs and the "days until too slow" model

Card: [EYKO-97](https://synverk.abdulhaque.dev/projects/bc6e8969-e244-4916-b158-2903baf02996/tasks/97).
Answers B2, B4, B7, C2 and "show me graphs, especially for mobile".
**Waits for EYKO-91** (laptop CSV). Phone CSVs from EYKO-95 (Infinix) and EYKO-93 / EYKO-96
join when ready. Branch: `taha/eyko-97-vectors-plots`.
Outputs: `src/benchmarks/plot_vector_storage.py`, task `vectors-plots`,
`docs/results/vectors/plots/*.png|svg`, `docs/results/<date>-vectors-graphs-and-capacity.md`.

## What can start before EYKO-91 lands

The Pixel and A32 sweep CSVs from 3 Nov are already committed. The script and graphs 1–4 and
7 can be built and tested against them now. When the laptop CSV arrives, re-running
`task vectors-plots` redraws everything, which is the card's own "done" test.

## Script design

- `glob("docs/results/vectors/*.csv")` → one pandas DataFrame. Accept the extra `note` and
  `recall_at_20` columns if present. Drop rows with empty `median_ms` (skipped / OOM), but
  **keep them for annotation**: an OOM is a result, so draw it as an ✕ at its size.
- Aggregate per (device, method, n, source_vectors): the median of the 5 run medians, with
  p95 as the error bar (as the card says).
- **Fixed colour per device** in a dict (laptop, Pixel 9 Pro XL, Samsung A32, Infinix Note
  12, Zara's phone), plus line style per method. Unknown devices get the next colour from a
  fixed palette, so a new phone never breaks the script.
- Write each figure as PNG (150 dpi) and SVG. Recreate the output folder each run so stale
  graphs cannot survive.
- Dependencies: `uv run --with matplotlib --with pandas python src/benchmarks/plot_vector_storage.py`
  in the Taskfile (neither is a project dependency today). Keep the file under 300 lines.
  If it gets close, move each graph function to `_vector_plots.py`.

## The seven graphs: data source and status

| # | Graph | Data | Can draw today? |
|---|---|---|---|
| 1 | **Search time vs vector count**, log x 1k–300k, one line per method × device, dashed 200 ms | All sweep CSVs | Yes (Pixel, A32). Laptop after EYKO-91 |
| 2 | Memory (PSS) vs vector count, for 1, 2 and 3 tables, per device | Sweep `pss_mb` today is **one table**. 2–3 tables need EYKO-100 (lead, honest PSS) | Partly: one-table line now, plus a computed line for the theoretical 2 KB × n × tables |
| 3 | DB file size vs n: BLOB vs sqlite-vec | `file_mb`; sqlite-vec from the laptop CSV | After EYKO-91 |
| 4 | Same test, laptop vs Pixel vs Zara's phone: bars, log y | Pick n = 20k, `blob_memory_dot` | Pixel + A32 now |
| 5 | Storage per hour of video: DB, frame files, total | EYKO-96 | No, placeholder text until it lands |
| 6 | Heat: cool vs hot vs low battery at 20k and 100k | EYKO-95 / EYKO-90 protocol runs | No |
| 7 | **Days until search passes 200 ms** vs hours per day, per phone | Graph 1 data + formula below | Yes |

For graphs whose data is missing, the script should **skip the graph and print one line
saying which CSV it waits for**. It must not draw an empty axis that looks like a result.

## The capacity model (graph 7), worked through with today's numbers

The card's inputs:

- Kept frames per minute: **r = 13.4** (Ego4D Pixel run: 372 in 27.8 min). Re-check this
  against EYKO-96 data, and show it as a band (e.g. 10–16, per the Head 4 "10–16 per 75 s"
  figure, which is 8–13 per minute) so the result does not rest on one clip set.
- Vectors per day = h × 60 × r, where h is hours recorded per day.

**Correction to raise with the lead.** The card multiplies by the number of tables. Search
time depends on one table (search scans `image_vec` only, `VideoSearch.kt`), so for the
time limit it is `vectors/day = h × 60 × r` per table. **Memory** is what adds across tables
(image 2 KB + text 1.5 KB + later audio 2 KB per kept frame). Two limits, two formulas:

```
N_200   = size where the phone's time-vs-n curve reaches 200 ms   (from graph 1 data)
N_mem   = usable heap / bytes per kept frame across all tables       (from graph 2 data)
days_time = N_200 / (h · 60 · r)
days_mem  = N_mem / (h · 60 · r)
days_until_limit = min(days_time, days_mem)
```

**Finding N_200.** The relation is close to linear, with cache effects at large n. Use
**piecewise-linear interpolation in log-log space** between the measured sizes on either
side of 200 ms. Do not fit a straight line through all the points, because the small sizes
are dominated by fixed overhead. Report the two neighbouring measured points so anyone can
check the result.

Today's numbers (run medians, random vectors, so provisional):

| Phone | Bracketing points | N_200 ≈ | days at 1 h/day | 2 h/day | 4 h/day |
|---|---|---|---|---|---|
| Pixel 9 Pro XL | 50k → 108.6 ms, 100k → ~270 ms | **~78k** | ~97 | ~48 | ~24 |
| Samsung A32 | 20k → 80.5 ms, 50k → 252.6 ms | **~41k** | ~51 | ~25 | ~13 |

(1 h/day = 60 × 13.4 = 804 kept frames per day.)

Memory limit, Pixel: the heap growth limit is 256 MB and float32 512-d is 2 KB, so in theory
~130k vectors for `image_vec` alone. In practice the cache reload holds the old and the new
array at once, and the app has other memory too, so the safe ceiling is lower. The 300k run
hit `OutOfMemoryError` on a 614 MB allocation. With `text_vec` added (3.5 KB per kept frame),
the 256 MB heap is shared across tables. The write-up must say that **on the Pixel, memory
and not speed may be the first wall, depending on how many tables are loaded at once**.

Graph 7 axes: x = hours recorded per day (0.5–8), y = days (log). One line per phone for
`days_time`. A dashed line of the same colour shows `days_mem` where a heap limit is known.
Shade the band from r = 8 to 16.

## Approaches for the capacity model, compared

| Approach | Pros | Cons |
|---|---|---|
| **A. Interpolate measured points** (recommended) | No model assumption, every number traceable to a CSV row | Cannot go beyond the largest measured size (fine: the limit falls inside the range on both phones) |
| B. Fit t = a + b·n per phone | One clean formula for the write-up | Hides the super-linear jump at 100k on the Pixel (cache) |
| C. Analytic: FLOPs / measured GFLOPS | Explains *why* | Not what the examiner asked; too many assumptions |

Show A in the graph, and B's slope in a sentence ("about 2.7 µs per vector on the Pixel, 5 µs
on the A32") because it is easy to say out loud in the defence.

## The write-up: two lines per graph

For each graph, write "what this shows" and "what it does not show", for example for graph 7:

- *Shows:* with the current brute-force search, a user recording 1 hour a day passes 200 ms
  after about 3 months on the Pixel and about 7 weeks on the A32.
- *Does not show:* random vectors, one table, a cool phone (except where graph 6 data
  exists). It assumes no faster search loop. EYKO-100 may move these limits a long way.

End with the direct answer to B2 ("when does a real user hit the limit?") as a small table
per phone, and point B7 at the EYKO-89 / EYKO-91 recommendation.

## Done-when checklist

- [ ] `task vectors-plots` reproduces every available graph from committed CSVs with one command
- [ ] Missing-data graphs are skipped with a printed reason, never drawn empty
- [ ] Consistent device colours across all graphs; log scales and the 200 ms line as specified
- [ ] Capacity formula, every input, and both limits (time, memory) in the write-up
- [ ] Two-line reading per graph
- [ ] PR, card to Review
