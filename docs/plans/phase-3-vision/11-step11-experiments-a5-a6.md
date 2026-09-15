# Step 11 — Experiment A5–A6: Cross-Pipeline Quality & Model Comparison

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

## Experiment A6: Gemma 4 E2B vs Dedicated VLMs (Shared Architecture Test)

### Hypothesis
Gemma 4 E2B (already loaded for answer generation) can produce captions comparable to dedicated VLMs (Moondream2/PaliGemma). Using it as a "Shared Model" eliminates the need for a separate VLM, saving ~1–2GB of RAM on the mobile device.

### Method
1. Select the same 20 test frames used in A1.
2. Caption each frame with three candidates:
   - **Gemma 4 E2B** (Shared Model via LiteRT-LM, FP16/INT8)
   - **Moondream2** (Dedicated VLM via llama.cpp, 1.8B Q4 GGUF)
   - **PaliGemma** (Dedicated VLM via llama.cpp, 3B Q4 GGUF)
3. Measure per model: caption quality (blind human eval 1–5), inference latency, and **Total AI System RAM** (VLM + LLM + Embedder).
4. Run the 10 video QA queries against memories from each model.
5. Compare retrieval accuracy (MRR, Hit@5).

### Output Table
| Model Strategy | Total System RAM | Caption Quality | Latency (s/frame) | Hit@5 | MRR |
|---|---|---|---|---|---|
| Gemma 4 E2B (Shared) | **~2.4 GB** (0 extra) | — | — | — | — |
| Moondream2 (Separate)| ~3.4 GB (+1GB) | — | — | — | — |
| PaliGemma (Separate) | ~4.0 GB (+1.6GB)| — | — | — | — |

### Decision Matrix
| Factor | Weight | Gemma 4 (Shared) | Moondream2 | PaliGemma |
|---|---|---|---|---|
| RAM Efficiency | 40% | — | — | — |
| Inference Speed | 20% | — | — | — |
| Caption Quality | 25% | — | — | — |
| Retrieval Acc. | 15% | — | — | — |

### Success Criteria
- If Gemma 4 E2B supports vision and its caption quality is within 15% of the best dedicated VLM, it wins purely on the massive RAM efficiency advantage (saving 1GB+).
- This is the "killer slide" for the defense presentation, proving deep architectural optimization.

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
  desc: Compare Moondream2 vs PaliGemma for video captioning
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
