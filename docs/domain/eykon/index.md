# Eykon — Project Domain Index

> Refreshed 12 October 2026. The current plan is the **Synverk board**
> (project Eykon, key `EYKO`, through the `synverk` MCP server in
> `.mcp.json`). `docs/plans/` holds background, method and the older phase
> plans. Where they disagree, the Synverk card wins.

## Identity

- **Project Code:** F26-220-Eykon
- **Type:** FYP (Final Year Project)
- **Status:** Re-defense required (panel rejected first defense)

## What we are building

A **second brain**: a persistent, local-first memory for a phone. It reads
video (and its sound), keeps the moments worth remembering with their
context in SQLite, and later answers questions with proof (the frame, the
time, the quote). Nothing leaves the device at runtime.

Priority order of what it must do:

1. **Find objects** — "where are my keys?", "where were they yesterday?"
2. **Speech and actions** — "what did I say about X?", "what was I doing?"
3. **Sounds without words, meetings and lectures** — important, later.

## The central decision: cheap models first, VLM optional

The first plan captioned every frame with a vision-language model (Gemma 4
E2B). Our own measurements showed that is too heavy for a phone (laptop soak
test about 13 s per frame; Infinix Note 12 averaged 4.68 W). The same job is
now done by small specialised models, and the VLM stays only as an optional
last resort. **Both paths are run on the same videos and questions so cost
and accuracy are compared with measurements** (card EYKO-33).

## Architecture (current)

```
Video → queue → ffmpeg (frames + audio)
  frames → cheap filters → unique frames → perception → scene record ─┐
  audio  → speech segments → transcript ──────────────────────────────┤
                                          embeddings + keyword index ←┘
                                          → link to video and moment
                                          → latest sighting per object
                                          → SQLite
Question → date filter → search (frames, text vectors, keywords[, sounds])
         → rank fusion (RRF) → answer with proof (LLM optional)
```

Perception options all write the same scene record, so they can be swapped
and compared:

| Option | What | Role |
|---|---|---|
| A | YOLOX-Tiny (ONNX) + MobileCLIP prompts + hand-centred crop matching for small objects | Default, start here |
| B | Small clip action model | Only if A misses actions |
| C | Small VLM caption (Gemma 4 E2B path in `src/vision/` is the reference) | Last resort and comparison baseline |

Flows on Synverk: "Eykon Ingestion & Retrieval Flow" (the pipeline),
"Eykon Memory Map" (the tables), "Eykon Retrieval Sequence" (one question).

## Laptop and phone

**The product is built once, on the phone. The laptop is only a lab**
(decided 12 October 2026). Picking a video, storing it, processing, the
database, search and the answer screen are written in Kotlin inside the
existing Android app. The laptop answers model questions with plain scripts
(which model finds the objects, which thresholds) and exports the winning
model for the phone; it does not get its own job queue, pages or
notifications. To keep the two sides honest: the same SQLite table design
(`src/video_memory/schema.py` is the contract), the same ONNX model files,
the same maths for the cheap filters, and golden frames whose results must
match on both.

Phones: Pixel 9 Pro XL (the capable phone) and Samsung A32 (the modest one,
standing in for the Infinix Note 12). Results are shown for both so the
cost is visible.

**How the cards are worked:** the existing cards are followed in their own
order (EYKO-1, 2, 3, …), each one built into the Android app, with the
cheap models in place of the VLM. A card's laptop text is the behaviour to
match; the phone code is its real home.

**Next milestone:** supervisor demo, Thursday 15 October 2026, 3 PM.

## Tech Stack

| Layer | Technology | Status |
|---|---|---|
| Language | Python 3.11+ (lab), Kotlin (phone) | in use |
| UI | Streamlit (lab), Jetpack Compose (phone) | in use |
| Text embeddings | `BAAI/bge-small-en-v1.5` (384-dim), MIT; on the phone as the repository's own ONNX file with a Kotlin WordPiece tokenizer | in use on the laptop; on the phone for video captions (EYKO-12). The phone's memory search still has no embedder switched on |
| Image embeddings | MobileCLIP-S2 image encoder as ONNX (512-dim). Weights under the Apple ML Research Model License: research and academic use only, never shipped in the app package | in use on the phone (EYKO-6) |
| Search by typed phrase | MobileCLIP-S2 text encoder as ONNX (254 MB, same licence as the image encoder) + CLIP tokenizer in Kotlin; nearest stored frame vectors | on the phone (core of EYKO-19); date range, latest-only and the question set are not built yet |
| Detector | YOLOX-Tiny, Apache-2.0, ONNX Runtime | on the phone (EYKO-9). Chosen over Nano on 13 October 2026: 18 against 4 of 32 everyday things in our frames, 244 against 102 ms per frame on the Pixel. Still misses about half, and phones most of all: `docs/results/2026-10-13-eyko-9-perception-option-a.md`, `docs/results/2026-10-13-frame-search-probe.md` |
| Speech | faster-whisper small int8 = laptop baseline; phone engine (whisper.cpp tiny.en / base.en) measured at the phone gate | planned (EYKO-8) |
| Sound embeddings | CLAP | optional, later (EYKO-13) |
| LLM | Gemma 4 E2B-it via LiteRT-LM — optional answer layer | in use (text RAG) |
| Database | SQLite (`data/memories.db`), raw `sqlite3`, FTS5 | in use |
| Vector storage | float32 BLOB columns, loaded into memory once, dot-product search (no sqlite-vec) | decided (EYKO-31, `docs/results/`) |
| Search | Dense cosine + BM25 fused with RRF (k=60) | in use |
| Config | Pydantic Settings (`MEMORY_` prefix) | in use |
| Package manager / tasks | `uv`, `Taskfile.yml` | in use |
| Tests | pytest | decided (EYKO-30) |

Rules: AGPL allowed while academic only, re-decide before shipping (`docs/invariants/tooling.md`); no ORM; every model must have a phone-ready form.

## Folder Structure

```
src/
├── memories/          # Text RAG core: models, embedder, repository, search, service, reranker, query
├── assistant/         # LLM: llm.py, prompt.py, helpers.py
├── vision/            # VLM video pipeline (Phase 3) — the Option C reference
├── video_memory/      # NEW: the Synverk pipeline (created by card EYKO-1)
├── ui/                # Streamlit app
├── benchmarks/        # Benchmark runner, metrics, data, experiments
└── config.py          # Pydantic Settings
android/               # Kotlin + Compose app
```

## Where things stand

| Work | Status |
|---|---|
| Phase 1 — Text RAG on desktop | ✅ Complete |
| Phase 2 — Android app + audio capture | Steps 01–05 done; 06–07 folded into the phone gate |
| Phase 3 — VLM vision pipeline (pre-recorded video) | Steps 01–10 done; kept as the VLM reference. Remaining audit / citation / re-defense work is card EYKO-35 |
| Phase 2 remaining steps (06 full UI, 07 integration test) | Dropped as written; the app is repurposed for video (phone track) |
| EYKO-30 (pytest), EYKO-31 (storage spike), EYKO-1 laptop tables | Done and pushed |
| EYKO-1 and EYKO-2 on the phone (video tables, pick and store a video) | Built, awaiting a phone test |
| EYKO-3 onward | Next, in card order, on the phone |
| EYKO-36 … 43 (a separate demo card list) | Withdrawn; not used |
| EYKO-33 (measured comparison), 34 (phone gate), 35 (defense package) | After the demo |
| Older phase plans 3.1 – 8 in `docs/plans/` | Background and method (probes, gates, pessimist rules, KPIs). Not the active task list |

## Key Constants (Phase 1 — Locked)

| Constant | Value |
|---|---|
| Chunk size | 256 tokens |
| Overlap | 40 tokens |
| Chunk ceiling | 400 tokens |
| Embedding dim | 384 |
| Top-K | 5 |
| Pool-K | 20 |
| RRF k | 60 |
| Query expansion | ON (static concept map) |
| Reranking | ON (cross-encoder) |

## Benchmark Results (Phase 1 — Baseline)

| Metric | Value |
|---|---|
| Hit@1 | 76.67% |
| Hit@5 | 93.33% |
| MRR | 0.8344 |
| Corpus | 499 memories (50 gold + 449 noise) |
| QA pairs | 30 |

## VLM reference path (Phase 3 decisions, kept for the comparison)

| Decision | Choice |
|---|---|
| VLM | Gemma 4 E2B-it (shared with the answer model) |
| Runtime | LiteRT-LM (primary) + llama.cpp (benchmarks) |
| Inference | CPU-only (simulating mobile ARM) |
| RAM budget | ≤ 4GB total for all AI models |
| Frame sampling | 1 per 5 seconds (configurable) |
| Dedup | discard if >0.95 similarity to the previous frame |

Phase 3 experiments A1–A4 exist but several rest on very small samples
(see `docs/plans/00-roadmap.md` section 9); they are smoke tests, audited in
card EYKO-35.
