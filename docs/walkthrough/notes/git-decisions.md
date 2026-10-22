# Notes from the git log, for the decisions phase

Source: `git log` on branch `feature/video-memory`, 61 commits from
5 September to 21 October 2026, read 22 October 2026. Every commit message
is a subject line only (no bodies), so the *why* behind a decision has to come
from the docs the commit added or changed. Each row names that doc. A row
marked "reason not in the commit" means the commit shows *what* changed and
the reason has to be found elsewhere, or tagged [UNKNOWN], in Phase 2.

All commits are authored as `Rafique610`. The current git user is `TahaGPT`.

## Major decisions, oldest first

| Date | Commit(s) | Decision (what changed) | Where the reason is written |
|---|---|---|---|
| 5 Sep | `c34850b`, `bb65a99`, `f87db87`, `152abec` | Phase 1 laptop RAG: raw SQLite, BAAI/bge-small-en-v1.5 (384-d), token chunking 256/40/400, dense cosine + SQLite FTS5 BM25 fused by RRF | `docs/plans/done/01-phase1-implementation.md`, step docs `✅ 02`–`✅ 05`; `docs/additional/architecture-overview.md` "Why These Choices" |
| 5 Sep | `a2ba436` | Answers from Gemma 4 E2B through **LiteRT-LM** instead of Ollama. The Ollama settings stay in `src/config.py:19-20` and `ollama` stays in `pyproject.toml`, unused | `docs/plans/done/✅ 06-step06-generation-llm.md:15`. The same doc still contains the Ollama code (lines 72–157), so it was only partly rewritten |
| 5 Sep | `97cfcb7`, `4c3433a` | Phase 1.1: static query expansion, pool widened to 20, cross-encoder re-rank (`cross-encoder/ms-marco-MiniLM-L-6-v2`) | `docs/plans/done/02-phase1.1-retrieval-improvement.md`, `✅ 09`–`✅ 12` step docs |
| 9 Sep | `a22c727` | Android app, Room SQLite, **minSdk 31** | `README.md:10` ("API 31 (Android 12)+ for Gemma 4 / LiteRT-LM"); `docs/plans/phase 2/✅ 01-step01-android-setup-storage.md` |
| 10 Sep | `8df89c2` | On-phone generation with LiteRT-LM, CPU backend forced; a LiteRT-LM AAR extract is committed under `scratch/litertlm/` (about 47 MB of `.so` files) | Comment in `android/app/src/main/java/com/eykon/memory/assistant/LiteRTGenerator.kt` ("avoid OpenCL discovery crash"); `docs/plans/phase 2/✅ 03-step03-litertlm-generation.md`. Why the AAR extract is committed: reason not in the commit |
| 10 Sep | `cf6eef2` | ONNX embedder and cross-encoder wrappers on the phone (`LocalEmbedder`, `LocalCrossEncoder`), never switched on | `docs/domain/eykon/index.md:92` ("The phone's memory search still has no embedder switched on"); `README.md:60` |
| 15 Sep | `d76784c`, `86aefc0`, `86ebe2e`, `3d184ea` | Phase 3 VLM path on the laptop: OpenCV frame sampling, VLM captions, captions stored as text memories, Streamlit page | `docs/plans/phase-3-vision/✅ 01`–`✅ 07`; `docs/additional/literature-review.md` |
| 7 Oct | `23147b0` "final polish" | Adds Phase 3 experiments A1–A6, soak test, the `scratch/` adb/report scripts; captioner and extractor rewritten; `test_video.mp4` deleted while `Taskfile.yml` still uses it | Reason not in the commit; `docs/plans/phase-3-vision/✅ 08`–`✅ 10`, `11` |
| 12 Oct | `6af6101`, `33cca0e` | **Central pivot: cheap specialised models first, VLM optional.** Synverk board becomes the active plan | `docs/domain/eykon/index.md:27-34` (laptop soak ~13 s per frame; Infinix Note 12 averaged 4.68 W); `docs/new/eykon-roadmap-v2.md` |
| 12 Oct | `82cf088` | The product is built only on the phone; the laptop is a lab of scripts | `docs/domain/eykon/index.md:62-77` |
| 12 Oct | `61fb561`, `11b0485` | Vectors as float32 BLOBs, in-memory dot product; **no sqlite-vec** | `docs/results/2026-10-12-eyko-31-vector-storage.md` "Decision" (sqlite-vec failed to load on the phone; 81 ms at 20,000 vectors) |
| 12 Oct | `72a262b` | SQLite table as the job queue, resumable stages, 3 retries | Comments in `VideoJobs.kt`, `VideoWorker.kt`; reason for "no WorkManager" not in the commit |
| 12 Oct | `4e46158` | Split with the phone's own decoders: 3 frames/s, longer side ≤ 640 px, JPEG 90, 16 kHz mono WAV | Comments in `VideoSplit.kt:8-18` |
| 12 Oct | `c4e67ab` | Cheap filters before any model: dark, bright, blurry (variance of the Laplacian), unchanged; numbers must match OpenCV | `src/benchmarks/filters_golden.py` docstring; `README.md:54` |
| 12 Oct | `ff9872d` | Near-duplicates by 64-bit dHash (≤ 6 bits) then MobileCLIP-S2 cosine ≥ 0.95, compared with every unique frame so far | Comments in `VideoDedup.kt:11-20`; MobileCLIP licence: `src/benchmarks/export_clip.py` docstring |
| 12–13 Oct | `dde5e0e`, `e3fb8a0`, `b435c9d` | Keyframes: keep the sharpest frame of each 3 s slot (`SLOT_FRAMES = 9`) | `docs/results/2026-10-13-keyframes-slots-on-phone.md` (cost 137.5 → 32.6 s per minute; 34 → 31 of 35 moments; 3 behind uniform); `docs/results/2026-10-12-keyframes-tuning.md` ("uniform is hard to beat"); protocol `docs/plans/keyframe-comparison-protocol.md` |
| 13 Oct | `b8be6c8` | Perception Option A: **YOLOX-Tiny** (replacing Nano) + MobileCLIP place/action phrases | `docs/results/2026-10-13-eyko-9-perception-option-a.md:7` ("Decision ... the app uses YOLOX-Tiny"; Nano 4 of 32, Tiny 18 of 32) |
| 13 Oct | `1d0e557` | Small objects: hand crops (MediaPipe) rejected; grid tiles too costly | `docs/results/2026-10-13-eyko-32-hands-vs-grid.md` "What it means" |
| 13 Oct | `69cd6e5` | Scene record with a template caption built from the fields, no model | Comments in `VideoScene.kt`; `README.md:57` |
| 13 Oct | `8094215`, `7ca0a04` | Frame vectors stored; search by typed phrase with the MobileCLIP text encoder | `docs/results/2026-10-13-frame-search-probe.md` |
| 13 Oct | `50cf340` | Captions indexed by fts4 keywords and bge-small vectors on the phone (the search does not use them yet) | `README.md:60`; `.claude/skills/explain-pipeline/SKILL.md` ("indexes exist but are not used by search yet") |
| 13 Oct | `497b6b7` | The `link` stage checks and fails; it never repairs | Comment in `VideoLink.kt:8-13` |
| 13 Oct | `bb7191d` | Latest sighting per object: crop cosine ≥ 0.87 | `docs/results/2026-10-13-eyko-15-crop-threshold.md` (0.87: 15 of 48 same-object pairs missed, 3 of 288 different pairs merged) |
| 13 Oct | `99faff5` | Videos marked ready/failed, retry from the failed stage, only ready videos searched | Comments in `VideoJobs.kt`, `VideoSearch.kt` |
| 14 Oct | `93cf254`, `4a1ea55` | Small VLMs (Option C): licence and phone format checked, captions benchmarked against Option A | `docs/results/2026-10-14-vlm-licence-and-format-check.md`; `docs/results/vlm/` |
| 14 Oct | `e3702e3`, `452417b` | Open-vocabulary detectors measured: OWLv2 81 of 87 own things but ~4.7 s/frame (laptop), ~9 s (Pixel) | `docs/results/2026-10-14-detectors-open-vocabulary.md` |
| 15 Oct | `34fa3d3` | **AGPL models allowed while the project is academic** | `docs/invariants/tooling.md` (changed in this commit); same results doc, "Wider sweep after AGPL was allowed" |
| 15 Oct | `0794cfd` | D-FINE S (Objects365) joins YOLOX in `scene`; new `small_objects` stage with OWLv2 on MobileCLIP-picked frames. Pipeline `VERSION` 2 | `VideoPipeline.kt:36`; results doc above |
| 15 Oct | `7c86346` | Captions always name personal things first. `VERSION` 3 | `VideoPipeline.kt:37`; `VideoScene.kt` comment on `PERSONAL` |
| 15 Oct | `a3bc0d5`, `903b1f9` | **YOLOE-11L replaces OWLv2**, on every kept frame (55 vs 50 of 87 own things; +30 s vs +58 s per 75 s clip). `VERSION` 4 | `VideoSmallObjects.kt:14-23`; results doc "YOLOE-11L on the Pixel" |
| 19–21 Oct | `740efc8`, `6fb620f` | Ego4D episodic-memory evaluation: choose on set A, check on held-out set B | `docs/results/2026-10-19-ego4d-subset.md`, `2026-10-20-ego4d-baseline.md`, `2026-10-21-ego4d-improvements.md` |
| 21 Oct | `89b4da8` | Search windows (grow ≥ 0.85 × hit, gap ≤ 10 s), first-person action prompts with ±6 s smoothing, YOLOE only on MobileCLIP-flagged frames (≥ 0.15), dropped frame files deleted. `VERSION` 5 | `docs/results/2026-10-21-ego4d-improvements.md` results table; `VideoPipeline.kt:39`; `src/config.py:67-88` |

## Process decisions (not about the pipeline itself)

| Date | Commit | Decision | Where |
|---|---|---|---|
| 12 Oct | `471f78f` | pytest suite; the old one-line check renamed `smoke` | `Taskfile.yml` (`test`, `smoke`) |
| 12 Oct | `e1b6701` | Push the branch after each approved commit | `AGENTS.md` "Commits" |
| 17 Oct | `9c85b2f` | Project owner approval rule; `explain-pipeline` skill; recording plan v2 | `AGENTS.md` step 5; `.claude/skills/explain-pipeline/SKILL.md`; `docs/plans/dataset-recording/recording-plan-v2.md` |

## Things to settle in Phase 2

- `docs/results/2026-10-21-ego4d-improvements.md` marks change 4 (last seen
  with crops of any object, YOLOE-11S prompt-free) **Keep**, but commit
  `89b4da8` does not build it into `VideoLatest.kt`. Confirm in s07 and list
  it as a doc-vs-code gap.
- Change 3 (hybrid search over caption windows) is "Drop for now", which
  matches the phone search still using only frame vectors.
- `docs/additional/architecture-overview.md` still describes the
  September design (Ollama, `capture/text.py`, `retrieval/…` folders that
  do not exist). Record it as stale.
- Who decided what: results docs name "Rafique" as the decider (for example
  `docs/results/2026-10-13-eyko-9-perception-option-a.md:7`). Since
  16 October the project owner approves cards (`AGENTS.md`).
