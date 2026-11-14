# Sources

Every source was read or run on **5 November 2026**. Own probes live in [evidence/](evidence/).

| # | Title | Link / path | Used for |
|---|---|---|---|
| S1 | Card EYKO-91 | https://synverk.abdulhaque.dev/projects/bc6e8969-e244-4916-b158-2903baf02996/tasks/91 | steps, CSV format, pass mark |
| S2 | v1 script and write-up | `src/benchmarks/vector_storage_spike.py`, `docs/results/2026-10-12-eyko-31-vector-storage.md` | v1 methods, machine, numbers, Windows-only peak RSS |
| S3 | Phone benchmark code | `android/app/src/androidTest/java/com/eykon/memory/spike/BenchKit.kt`, `VectorStorageSpikeTest.kt` | how the phones build "real" vectors (90 + noise 0.01, queries noise 0.05, seeds 31 / 90), method names, CSV header with `note` |
| S4 | Phone results | `docs/results/vectors/*-2026-11-03-sweep.csv`, `*-2026-11-04-sweep-real.csv`, `*-2026-11-04-memory.csv` | what the phones already measured |
| S5 | Own-clip vector export | `src/benchmarks/export_own_vectors.py` | "never point this at a database with Ego4D clips" |
| S6 | Ego4D subset write-up | `docs/results/2026-10-19-ego4d-subset.md` | "Access is valid until 1 November 2026" |
| S7 | Head 2 figure script | `docs/documents/source/figures/vector_sweep.py` | reads `*-sweep-real.csv` by column name |
| S8 | Project rules | `docs/invariants/core.md`, `tooling.md`, `processes.md` | 300-line files, uv, licences, evidence before decisions |
| S9 | EYKO-89 research | branch `taha/eyko-89-android-sqlite-extensions`, `docs/results/eyko-89-android-sqlite-extensions/` | usearch as the index to test; O1 (float16 / int8) |
| S10 | Card EYKO-109 | https://synverk.abdulhaque.dev/projects/bc6e8969-e244-4916-b158-2903baf02996/tasks/109 | float16 / int8 recall mark 0.99 |
| S11 | sqlite-vec docs: vec0 and API reference | https://alexgarcia.xyz/sqlite-vec/features/vec0.html · https://alexgarcia.xyz/sqlite-vec/api-reference.html | `vec_quantize_i8` documented as a placeholder ("x", "todo") |
| S12 | Own probe: sqlite-vec 0.1.9 | `evidence/probe_sqlite_vec_int8.py`, `probe_sqlite_vec_ties.py` | int8 / cosine columns work; `vec_quantize_int8` is the real name; 'unit' uses 47–95 of 256 levels; float32 exact (the miss was a tie) |
| S13 | usearch Python README | https://github.com/unum-cloud/usearch/blob/main/python/README.md | API, defaults 16 / 128 / 64, `threads`, `exact`, `view` |
| S14 | Own probe: usearch 2.26.5 | `evidence/probe_usearch_defaults.py`, `probe_usearch_tuning.py` | default recall 0.20–0.25 on random 20k; 0.997 at c32 / ef1024 (8.3 ms) |
| S15 | Own probe: hnswlib | `uv --no-build --with hnswlib` (output in `evidence/probe-results-2026-11-05.txt`) | no wheel for Python 3.10 / Linux |
| S16 | Own probe: psutil 7.2.2 | command in `02` | PSS and peak RSS readable on Linux |
| S17 | EPIC-KITCHENS-100 page | https://epic-kitchens.github.io/2026 | CC BY-NC 4.0; ≈ 740 GB / 1.1 TB zipped |
| S18 | EPIC-KITCHENS download scripts | https://github.com/epic-kitchens/epic-kitchens-download-scripts | `--specific-videos`, `--participants`, Python 3.5+, no libraries |
| S19 | COCO terms of use | https://cocodataset.org/#termsofuse | **could not be read** with the fetch tool (page is built by script): licence to verify by hand |

## Looked for and not found

- EPIC-KITCHENS size per video: **not published** on the pages read; measure one download.
- MobileCLIP-S2 image-embedding speed on this CPU: **not measured yet**.
- Whether vectors derived from Ego4D clips may be used after access ended: **not settled**, so they are not used.
