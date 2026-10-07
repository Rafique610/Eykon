# Step 11 — Experiment A5–A6: Cross-Pipeline Quality & Model Comparison

> [!NOTE]
> **Realignment 05 Oct 2026 (additions only):**
> - A6 must report **per-frame latency on the phone too** (Pixel + Infinix) for
>   whichever models can run there, not only laptop CPU. Laptop-only numbers
>   go in a column labelled "laptop (emulation profile)".
> - Add a `## You test this` pass: for each model, you read 15 random captions
>   side-by-side with the frames and mark each *correct / partly / wrong /
>   hallucinated*. That human table is reported next to Hit@5.
> - `## How this number could be lying`: Hit@5 on 9 QA pairs from 3 clips can
>   be 100 % for every model; A6 ranking must lean on the human caption audit
>   and latency, not Hit@5.

## What
Two final experiments: (A5) verify that adding video memories doesn't break retrieval quality for existing text memories, and (A6) compare Moondream2 vs PaliGemma to justify our model choice.

## Why
A5 proves the architecture claim from PROJECT_SPEC: *"Storage and retrieval treat every memory record identically regardless of source-type."* A6 gives the panel a data-driven model comparison, not a hand-wavy "we picked the smallest one."

---

## Experiment A5: Cross-Pipeline Retrieval Quality (Regression Test)

### Hypothesis
Adding 50 video-sourced memories to the existing 499-memory benchmark database does not degrade retrieval accuracy by more than 5%.

### Method
1. Run the existing Phase 1 benchmark (`task benchmark --rerank --expand --pool-k 20`) → record baseline scores.
2. Process a test video → generate ~50 video memories → insert them into the benchmark DB.
3. Re-run the exact same 30 QA pairs.
4. Compare Hit@1, Hit@5, MRR before and after.

### Output Table
| Metric | Baseline (text only) | With 50 Video Memories | Delta |
|---|---|---|---|
| Hit@1 | — | — | — |
| Hit@5 | — | — | — |
| MRR | — | — | — |
| Avg Latency | — | — | — |

### Success Criteria
- All metrics within 5% of baseline
- No query that previously hit now misses (no regressions)

---

## Experiment A6: Comprehensive VLM Profiling (Gemma vs Moondream vs SmolVLM)

### Hypothesis
Different VLMs prioritize speed vs. accuracy. SmolVLM might be incredibly fast and achieve a 100% Hit@K rate by spotting objects (like "sunglasses"), but lacks the deeper conversational phrasing needed for high "True Answer Accuracy" when formulating the final response. We must profile them individually.

### Method
1. Select the standard test videos.
2. Run the full vision capture pipeline for each candidate individually:
   - **Gemma 4 E2B** (Shared Model via LiteRT-LM, FP16/INT8)
   - **Moondream2** (Dedicated VLM via llama.cpp, 1.8B F16 GGUF)
   - **SmolVLM** (Dedicated VLM via llama.cpp, 500M Q8 GGUF)
3. For **each model**, strictly record:
   - **Performance Speed:** Frames processed per second (latency/frame).
   - **Peak System Memory:** Total RAM footprint (VLM + LLM + Embedder).
   - **Retrieval Hit Rate:** Standard MRR and Hit@5 metrics.
4. Pass the generated captions to the QA LLM layer to assess if the resulting context allows the model to answer queries properly ("True Answer Accuracy" - to be deeply judged in A7).

### Output Table
| Model Strategy | Total System RAM | Latency (s/frame) | Hit@5 | Answer Context Quality (1-5) |
|---|---|---|---|---|
| Gemma 4 E2B (Shared) | **~2.4 GB** (0 extra) | — | — | — |
| Moondream2 (Separate)| ~3.4 GB (+1GB) | — | — | — |
| SmolVLM (Separate)   | ~2.7 GB (+300MB)| — | — | — |

### Decision Matrix
| Factor | Weight | Gemma 4 (Shared) | Moondream2 | SmolVLM |
|---|---|---|---|---|
| RAM Efficiency | 30% | — | — | — |
| Inference Speed | 20% | — | — | — |
| Context/Answer Quality| 50% | — | — | — |

### Success Criteria
- We must prove mathematically which model balances speed and memory without sacrificing the actual flow and context needed to satisfy the user's queries.

---

## Implementation

### 11.1 Script: `src/benchmarks/cross_pipeline.py`

```python
"""Experiments A5–A6: Cross-pipeline quality and model comparison.

Usage:
    uv run python src/benchmarks/cross_pipeline.py --experiment a5 --video test_video.mp4
    uv run python src/benchmarks/cross_pipeline.py --experiment a6 --video test_video.mp4
"""
```

### 11.2 Taskfile Entries

```yaml
experiment-a5:
  desc: Test video memory impact on existing retrieval quality
  cmd: uv run python src/benchmarks/cross_pipeline.py --experiment a5 --video test_video.mp4

experiment-a6:
  desc: Compare Moondream2 vs SmolVLM for video captioning
  cmd: uv run python src/benchmarks/cross_pipeline.py --experiment a6 --video test_video.mp4
```

## Verification
- [ ] A5 baseline matches known Phase 1 benchmark results (within ±2%)
- [ ] A5 "with video" run completes and shows delta table
- [ ] A6 runs both models and produces comparison table
- [ ] Decision matrix is populated with real scores
- [ ] Results saved to `data/experiment_a5_results.json` and `data/experiment_a6_results.json`

## Files Changed
- [NEW] `src/benchmarks/cross_pipeline.py`
- [MODIFY] `Taskfile.yml` — add `experiment-a5` and `experiment-a6` tasks

## Dependencies
- Step 06 (memory integration)
- Step 08 (benchmark utilities)
- PaliGemma model download (only needed for A6 — optional if time is short)

## Common Issues
- PaliGemma requires `google/paligemma-3b-pt-224` from HuggingFace, which needs a license agreement. Apply for access beforehand.
- If PaliGemma cannot be downloaded in time, run A6 with only Moondream2 and document "PaliGemma comparison deferred to Phase 3.1" — having one model's numbers is still valuable.
- A5 must use the EXACT same benchmark DB setup as Phase 1 to make the comparison valid. Use the same `GOLD_MEMORIES`, `CORPUS_MEMORIES`, and `QA_PAIRS` from `src/benchmarks/data.py`.
