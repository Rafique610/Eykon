# Eykon — Project Domain Index

## Identity

- **Project Code:** F26-220-Eykon
- **Type:** FYP (Final Year Project)
- **Use Case:** "Second Brain / Ambient Errand Assistant" — store video/audio/text context for later querying (e.g., "Where did I leave my keys?", "Summarize that conversation")
- **Status:** Re-defense required (panel rejected first defense)

## Architecture

Local-first, on-device personal memory app using RAG.

```
Capture (text/audio/video) → Chunk → Embed → Store (SQLite) → Search (Hybrid) → Rerank → Generate (Gemma 4) → Answer
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| UI | Streamlit |
| Embeddings | `BAAI/bge-small-en-v1.5` (384-dim) via `sentence-transformers` |
| LLM | Gemma 4 E2B-it via LiteRT-LM (2.6GB, confirmed multimodal) |
| VLM (Phase 3) | Gemma 4 E2B-it (shared model) + Moondream2/PaliGemma for benchmarking |
| Database | SQLite (`data/memories.db`) + FTS5 for keyword search |
| Search | Hybrid: Dense cosine + BM25 via RRF (k=60), optional cross-encoder rerank |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Config | Pydantic Settings (`MEMORY_` prefix) |
| Package Mgr | `uv` |
| Task Runner | `Taskfile.yml` |
| Mobile | Android (Kotlin + Jetpack Compose + LiteRT-LM) |

## Folder Structure

```
src/
├── memories/          # Core RAG: models, embedder, repository, search, service, reranker, query
├── assistant/         # LLM: llm.py, prompt.py, helpers.py
├── vision/            # Phase 3: extractor, captioner, processor (NEW)
├── ui/                # Streamlit app
├── benchmarks/        # Benchmark runner, metrics, data, experiments
└── config.py          # Pydantic Settings
```

## Phases

| Phase | Scope | Status |
|---|---|---|
| Phase 1 | Text RAG on desktop (Python + Streamlit) | ✅ Complete |
| Phase 2 | Android app + Audio capture | 🔄 In progress (4/7 steps done) |
| Phase 3 | Vision pipeline (pre-recorded video → memory RAG) | 📋 Planned (12 steps) |
| Phase 4 | Real-time modes (ambient memory + live query) | 📋 Future |

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

## Phase 3 Key Decisions

| Decision | Choice |
|---|---|
| Primary VLM | Gemma 4 E2B-it (shared model — confirmed multimodal, 0MB extra RAM) |
| Benchmark VLMs | Moondream2 (1.8B), PaliGemma (3B) |
| VLM Runtime | LiteRT-LM (primary) + llama.cpp (benchmarks) |
| Inference | CPU-only (simulating mobile ARM) |
| RAM Budget | ≤ 4GB total for all AI models |
| Frame Sampling | 1 per 5 seconds (configurable, tested at 1s/3s/5s/10s) |
| Storage | Semantic deduplication (discard if >0.95 similarity to previous frame) |
| 1-Year Storage Est. | ~300-500 MB (with dedup, 2 hrs/day) |

## Experiments (Phase 3)

| # | Tests | Purpose |
|---|---|---|
| A1 | Blind GGUF quantization evaluation | Prove Q4 is viable to skeptical panel |
| A2 | Frame sampling rate vs accuracy | Find optimal rate for mobile CPU |
| A3 | Short vs long captions | Optimize for retrieval + battery |
| A4 | 30-min CPU-only soak test | Prove thermal/memory stability |
| A5 | Video + text memory coexistence | Validate architecture |
| A6 | Gemma 4 vs Moondream2 vs PaliGemma | Prove shared model architecture |
| A7 | Optimization recovery | Recover any quantization quality drop |
