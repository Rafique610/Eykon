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
| A | YOLOX-Nano (ONNX) + MobileCLIP prompts + hand-centred crop matching for small objects | Default, start here |
| B | Small clip action model | Only if A misses actions |
| C | Small VLM caption (Gemma 4 E2B path in `src/vision/` is the reference) | Last resort and comparison baseline |

Flows on Synverk: "Eykon Ingestion & Retrieval Flow" (the pipeline),
"Eykon Memory Map" (the tables), "Eykon Retrieval Sequence" (one question).

## Laptop and phone

**Laptop is the lab, phone is the exam.** Options are tried and thrown away
on the laptop (Python). Only the option that wins the evaluation is ported
to the phone (Kotlin), checked against shared golden fixtures (card
EYKO-34). To keep the port small: prefer models with ONNX / TFLite exports
so the same file runs on both sides, keep the same SQLite schema, and spike
phone-only risks early (as card EYKO-31 did for vector storage).

## Tech Stack

| Layer | Technology | Status |
|---|---|---|
| Language | Python 3.11+ (lab), Kotlin (phone) | in use |
| UI | Streamlit (lab), Jetpack Compose (phone) | in use |
| Text embeddings | `BAAI/bge-small-en-v1.5` (384-dim) | in use |
| Image embeddings | MobileCLIP (512-dim) | planned (EYKO-6, 11) |
| Detector | YOLOX-Nano, Apache-2.0, ONNX Runtime | decided (EYKO-9) |
| Speech | faster-whisper small int8 = laptop baseline; phone engine (whisper.cpp tiny.en / base.en) measured at the phone gate | planned (EYKO-8) |
| Sound embeddings | CLAP | optional, later (EYKO-13) |
| LLM | Gemma 4 E2B-it via LiteRT-LM — optional answer layer | in use (text RAG) |
| Database | SQLite (`data/memories.db`), raw `sqlite3`, FTS5 | in use |
| Vector storage | float32 BLOB columns, loaded into memory once, dot-product search (no sqlite-vec) | decided (EYKO-31, `docs/results/`) |
| Search | Dense cosine + BM25 fused with RRF (k=60) | in use |
| Config | Pydantic Settings (`MEMORY_` prefix) | in use |
| Package manager / tasks | `uv`, `Taskfile.yml` | in use |
| Tests | pytest | decided (EYKO-30) |

Rules: no AGPL dependencies; no ORM; every model must have a phone-ready form.

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
| Synverk pipeline (cards EYKO-1 … 35) | All in backlog. First: EYKO-30 (pytest) and EYKO-31 (Android vector spike), then EYKO-1 |
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
