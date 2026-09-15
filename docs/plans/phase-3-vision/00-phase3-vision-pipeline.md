# Phase 3 — Vision Pipeline: Pre-Recorded Video → Memory RAG

## Goal

Build a complete **Video-to-Text RAG Pipeline** that processes pre-recorded video files, extracts visual context using a local VLM, stores the captions as memory records in the existing RAG pipeline, and allows the user to query them using natural language.

**Critical constraint:** Everything is built and tested on a laptop, but the **architecture, model format, inference runtime, and resource constraints must mirror what will actually run on a mobile device.** The laptop is a simulation/benchmarking environment for the mobile deployment — not the target platform.

This phase serves two purposes:
1. **Technical:** Validate the full video→caption→embed→store→retrieve→answer loop using mobile-compatible tools before porting to Android.
2. **Academic (Re-defense):** Generate the benchmark data, KPIs, and experiment results the panel demanded — proving model efficiency, resource consumption, and thermal viability on constrained hardware.

---

## Background / Panel Feedback Addressed

The FYP panel rejected the proposal citing:
- ❌ **Missing Literature Review** — addressed in Step 01 (research + LR document)
- ❌ **Weak PoC** — addressed by building a working end-to-end video pipeline using mobile-grade tools
- ❌ **No specific use case** — "Second Brain / Ambient Errand Assistant" (remember where I left things, summarize conversations, recall events from video)
- ❌ **No deployment plan for local model** — addressed by using the exact runtime (llama.cpp / GGUF) and model format that will run on Android
- ❌ **No KPIs for model efficiency** — addressed by Step 08–11 (dedicated benchmark suite measuring mobile-relevant metrics under constrained resources)

---

## Mobile-First Architecture Decisions

### Runtime & Model Format

The entire pipeline must use tools and formats that **directly translate to Android deployment**:

| Component | Mobile Target | Laptop Simulation |
|---|---|---|
| **VLM Inference Runtime** | llama.cpp (NDK/C++) on ARM | `llama-cpp-python` (same engine, same GGUF loader) |
| **VLM Model Format** | `.gguf` (quantized) | Same `.gguf` files — binary-identical |
| **LLM (Answer Gen)** | LiteRT-LM Gemma 4 E2B (already validated) | Same LiteRT-LM engine (already working) |
| **Embeddings** | ONNX Runtime Mobile or LiteRT | `sentence-transformers` on laptop (mobile port is Phase 2 scope) |
| **Frame Extraction** | Android `MediaCodec` | OpenCV on laptop (same interface contract) |
| **Storage** | Android Room (SQLite) | SQLite via `sqlite3` (same schema, same queries) |
| **Search** | Brute-force cosine + FTS5 | Same code (already validated in Phase 1) |

### Resource Constraints (Simulating Mobile)

Even though the laptop has 16GB+ RAM and an RTX 3050, benchmarks must measure against **mobile budgets**:

| Resource | Mobile Budget | How We Enforce on Laptop |
|---|---|---|
| **Total RAM for AI models** | ≤ 4 GB | Monitor and report peak RSS; flag if any run exceeds 4GB |
| **VLM model size on disk** | ≤ 2 GB | Use Q4_K_M or Q4_0 quantization (GGUF) |
| **Inference device** | CPU (ARM) or Mobile GPU (Vulkan) | Run llama.cpp on **CPU-only** (no CUDA) to simulate ARM performance |
| **Concurrent model memory** | VLM + Embedding model must co-exist | Measure combined RAM footprint |

> **Why CPU-only on laptop?** ARM CPU on a phone is ~2–5x slower than an x86 laptop CPU. By running CPU-only on the laptop, our latency numbers are a **lower bound** — if it's fast enough on laptop CPU, we know the ballpark for mobile. We document the expected mobile slowdown factor.

---

## Architecture — How Video Integrates With Existing Pipeline

The existing architecture (Phase 1) already normalizes all input into `MemoryRecord` objects with a `source_type` tag. The PROJECT_SPEC explicitly designed for this:

> *"Phase 3: Video/image input. An on-device vision-language step produces a text description of the frame/video, then treated as a normal memory record (source-type 'video')."*

### New Layer: Vision Capture Adapter

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Video File  │────▶│ Frame Sampler│────▶│   VLM Captioner  │────▶│  Existing    │
│  (.mp4/.avi) │     │ (1 per N sec)│     │ (Moondream2 GGUF │     │  RAG Pipeline│
│              │     │  + timestamp │     │  via llama.cpp)  │     │  (embed →    │
│              │     │              │     │                  │     │  store → ask)│
└──────────────┘     └──────────────┘     └──────────────────┘     └──────────────┘
                                                │
                                                ▼
                                    "[03:05] User placed car keys
                                     on the kitchen counter"
                                    → MemoryRecord(source_type="video")
```

### What stays the same (reused from Phase 1):
- `src/memories/` — embedder, repository, search, reranker, service (ALL reused as-is)
- `src/assistant/` — LLM engine, prompt builder (ALL reused as-is)
- `src/config.py` — Settings class (extended with new VLM settings)
- `src/ui/app.py` — Streamlit UI (extended with video upload page)
- `src/benchmarks/` — metrics module (reused, new vision benchmarks added)

### What is new:
- `src/vision/` — new feature folder (frame extraction, VLM captioning via llama.cpp, video processing orchestrator)

---

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| VLM Runtime | **LiteRT-LM** (Primary) and **llama.cpp** (Benchmark) | LiteRT-LM is already validated and running. Using the same runtime for both VLM and LLM means one engine, one model, one deployment. |
| VLM Model (Primary Candidate) | **Gemma 4 E2B-it (already loaded)** — Confirmed multi-modal! | Zero additional RAM cost. The screenshot confirms this variant supports multi-modality natively. Revolutionary simplification for the pipeline. |
| VLM Model (Fallback/Benchmark) | **Moondream2 (1.8B) / PaliGemma** | Tested head-to-head against Gemma to prove to the panel that the shared architecture doesn't sacrifice quality. |
| Inference Device | **CPU-only** (mobile simulation) | Phones don't have CUDA. We benchmark on CPU to get representative latency. |
| Frame Sampling Rate | **1 frame per 5 seconds** (configurable) | Experiment A2 will find the optimal rate for mobile CPU throughput. |
| Caption Storage | Reuse existing `MemoryRecord` with `source_type="video"` | Zero changes to storage/retrieval layer. |
| RAM Budget | **≤ 4 GB total** for all AI models | With Gemma 4 doing double-duty, total AI RAM = just ~2.6GB (one model for everything). |

### The "Shared Model" Architecture (CONFIRMED)

```
                    ┌─────────────────────────────┐
                    │   Gemma 4 E2B-it (LiteRT)   │
                    │   Already loaded (2.6 GB)    │
                    │                             │
     ┌──────────────┤  Input: Image + Prompt      │
     │              │  Output: Caption text        │──── "User placed keys on counter"
     │              │                             │           │
     │              │  Input: Question + Context   │           ▼
     │              │  Output: Answer text         │──── "You left your keys on the
     │              │                             │      kitchen counter at 3:05 PM"
     │              └─────────────────────────────┘
     │
  Video Frame
  (1 per 5s)
```

**vs. the traditional two-model architecture:**
```
  Video Frame ──▶ [Dedicated VLM (+1-2GB)] ──▶ Caption ──▶ [Gemma 4 (2.6GB)] ──▶ Answer
```

---

## Working Assumptions to Test (Experiments)

| # | Assumption | Experiment | Success Metric |
|---|---|---|---|
| A1 | **Quantized models are NOT significantly worse** | Blind side-by-side comparison: Q4 vs Q8 vs FP16 captions evaluated by humans | ≥80% of evaluators rate Q4 as "equivalent or acceptable" |
| A2 | 1 frame per 5 seconds captures enough context | Process test video at 1s, 3s, 5s, 10s intervals | Hit@5 at 5s ≥ 70% of 1s |
| A3 | Short captions embed better than paragraphs | Compare 1-sentence vs multi-sentence captions | Short MRR ≥ 90% of long |
| A4 | System runs 30+ min on CPU without thermal throttle | CPU-only soak test with RAM and latency monitoring | Zero crashes, latency drift < 20% |
| A5 | Video memories coexist with text memories | Add 50 video memories to benchmark DB | Existing scores within 5% of baseline |
| A6 | **Gemma 4 E2B matches dedicated VLMs** | Compare Gemma 4 E2B vs Moondream2/PaliGemma | Gemma 4 wins purely on the massive 1GB+ RAM efficiency advantage. |
| A7 | **Other optimizations recover quantization drops** | Test: better prompts, multi-frame context aggregation | Combined optimizations recover ≥50% of any gap |

---

## Steps

### Step 01 — Literature Review & Research Document
### Step 02 — Environment Setup & VLM Model Download (llama.cpp + GGUF)
### Step 03 — Frame Extraction Module
### Step 04 — VLM Captioning Module (llama.cpp backend)
### Step 05 — Video Processing Orchestrator (End-to-End Pipeline)
### Step 06 — Integration With Existing Memory Pipeline
### Step 07 — Streamlit UI: Video Upload & Processing Page
### Step 08 — Benchmark Suite: Mobile-Relevant VLM Performance Metrics
### Step 09 — Experiment A1–A3: Quantization (GGUF), Sampling Rate, Caption Style
### Step 10 — Experiment A4: Sustained Processing (Thermal/Memory Soak Test, CPU-only)
### Step 11 — Experiment A5–A6: Cross-Pipeline Quality & Model Comparison
### Step 12 — Re-defense Documentation Package

---

## Resolved Decisions

| Question | Decision |
|---|---|
| **Test video** | Download a short 15–20 second video from YouTube for initial development. Scale up to longer videos for experiments. |
| **GPU** | NVIDIA RTX 3050 (6GB VRAM) available, but **benchmarks run CPU-only** to simulate mobile ARM. GPU used only for optional "GPU vs CPU comparison" data point. |
| **Model comparison** | ✅ Proceeding with Moondream2 vs PaliGemma/SmolVLM comparison (Experiment A6). Both must be in GGUF format. |

---

## Verification Plan

### Automated Tests
- `task test-vision` — Verify frame extraction produces correct count of frames
- `task benchmark-vision` — Run full VLM benchmark suite on CPU-only (mobile simulation)
- `task test` — Existing RAG tests must still pass (regression check)

### Manual Verification
- Process a real video → query it → verify answers are grounded
- Demonstrate the Streamlit UI video upload flow end-to-end
- Review benchmark charts for re-defense presentation

---

## Dependencies

- **Python packages (new):** `opencv-python`, `llama-cpp-python`, `Pillow`, `psutil`
- **Model files:** Moondream2 GGUF Q4_K_M (~1GB), optionally PaliGemma/SmolVLM GGUF (~1–2GB)
- **Existing:** All Phase 1 modules (`src/memories/`, `src/assistant/`, `src/benchmarks/`)
- **Hardware:** Laptop with CPU (benchmarks are CPU-only to simulate mobile)
