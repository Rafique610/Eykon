# Step 09 — Experiment A1–A3: Quantization (GGUF), Sampling Rate, Caption Style

## What
Run three controlled experiments using **GGUF quantization levels** (not PyTorch BitsAndBytes), tested on **CPU-only** inference to validate assumptions under mobile-realistic conditions.

## Why
The panel wants evidence-based decisions, not assumptions. These experiments produce comparative data using the exact same model format and runtime that will deploy on the phone.

---

## Experiment A1: Blind Evaluation of GGUF Quantization

### Hypothesis
Q4 quantization (which fits our mobile RAM budget) does NOT noticeably degrade caption quality compared to Q8/FP16. We will prove this to the panel via a blind A/B/C test.

### Method
1. Select 20 diverse test frames from the test video (varied scenes).
2. Caption each frame using the **same model** at different quantization levels:
   - Model GGUF Q8_0 (baseline — largest, best quality)
   - Model GGUF Q5_K_M (medium compression)
   - Model GGUF Q4_K_M (target for mobile — best quality/size ratio)
3. **Blind Human Evaluation:** Present the 20 sets of captions to human evaluators without labels (e.g., "Caption A", "Caption B", "Caption C"). Ask them to rate each 1–5 on accuracy and detail.
4. Unblind the data and calculate the average score for each quantization level.
5. Automated evaluation: cosine similarity between Q8 and Q4 captions using the embedding model.

### Output Table
| GGUF Variant | File Size (MB) | RAM (MB) | Latency (s, CPU) | Blind Human Eval (1-5) | Cosine Sim to Baseline |
|---|---|---|---|---|---|
| Q8_0 (baseline) | — | — | — | — | 1.000 |
| Q5_K_M | — | — | — | — | — |
| Q4_K_M (target) | — | — | — | — | — |

### Mobile Relevance
- The panel believes quantization ruins performance. A blind test is undeniable empirical evidence.
- Q4_K_M is our target because it fits in ~1GB RAM on a phone.

### Success Criteria
- Q4_K_M blind rating is within 0.5 points of Q8_0 rating (e.g., 4.1 vs 4.5).
- Q4_K_M cosine similarity to baseline >= 0.85
- Q4_K_M RAM < 50% of Q8 RAM

---

## Experiment A2: Frame Sampling Rate vs Retrieval Accuracy

### Hypothesis
Sampling 1 frame every 5 seconds captures enough visual context for "where did I leave X?" queries, with negligible accuracy loss compared to 1-second sampling.

### Method
1. Use a 15–20 second test video with 3–5 known "events" (e.g., person picks up object, places it down, moves to another spot).
2. Create 5–10 ground-truth QA pairs tied to specific timestamps.
3. Process the video at 4 intervals: 1s, 3s, 5s, 10s — all using **CPU-only** llama.cpp.
4. For each interval, store captions → embed → run all queries.
5. Measure: Hit@3, total processing time, total memories stored, total pipeline time.

### Output Table
| Interval | Frames | Processing Time (CPU) | Memories | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|---|---|
| 1s | ~15-20 | — | — | — | — | — |
| 3s | ~5-7 | — | — | — | — | — |
| 5s | ~3-4 | — | — | — | — | — |
| 10s | ~1-2 | — | — | — | — | — |

### Mobile Relevance
- On a phone with 10–30s/frame latency, processing at 1s interval is physically impossible (model can't keep up)
- We need to find the interval where accuracy is acceptable AND the phone can keep up
- The "mobile-viable interval" = max(latency, desired_interval)

### Success Criteria
- Hit@3 at 5s interval >= 70% of Hit@3 at 1s interval
- Processing time at 5s < 25% of processing time at 1s

---

## Experiment A3: Short Captions vs Long Descriptions for Retrieval

### Hypothesis
Single-sentence captions embed better for retrieval than multi-sentence paragraph descriptions, and they are faster to generate (fewer output tokens = less CPU time on mobile).

### Method
1. Select 20 test frames.
2. Caption each with two different prompts via llama.cpp (CPU-only):
   - **Short:** "Describe what you see in one sentence."
   - **Long:** "Describe everything you see in detail, including objects, colors, positions, and any text visible."
3. Store both sets as memories (separate DBs).
4. Run 10 retrieval queries against each set.
5. Measure: MRR, Hit@5, average caption token count, inference latency per caption, embedding latency.

### Output Table
| Style | Avg Tokens | Gen Latency (s, CPU) | Embed Latency (ms) | Hit@5 | MRR |
|---|---|---|---|---|---|
| Short (1 sentence) | — | — | — | — | — |
| Long (paragraph) | — | — | — | — | — |

### Mobile Relevance
- Shorter captions = fewer output tokens = faster generation on ARM
- If short captions retrieve equally well, we save 50–70% CPU time per frame
- This directly affects battery life on 2-hour sustained use

### Success Criteria
- Short captions achieve >= 90% of long captions' MRR
- Short captions generate 2x+ faster (fewer output tokens)

---

## Experiment A7: Recovering Quantization Drop via Other Optimizations

### Hypothesis
If Experiment A1 shows a slight quality drop from quantization, we can recover it through other zero-cost optimizations (better prompting, multi-frame context aggregation, and semantic chunking) without needing a larger model.

### Method
1. Take the Q4_K_M outputs from A1 that performed worst.
2. Apply three optimization techniques:
   - **Prompt Engineering:** "Describe the key objects, actions, and locations in this scene as a single factual statement."
   - **Context Aggregation:** Instead of embedding frames individually, combine captions from 3 adjacent frames (e.g., [t=0, t=5, t=10]) into a single "scene memory".
   - **RAG query expansion:** Expand the user's query at search time (already implemented in Phase 1, but we measure its impact on vision specifically).
3. Measure retrieval Hit@5 with and without these optimizations.

### Mobile Relevance
- Proves to the panel that we don't just rely on "raw model quality" — we use systems engineering to make small, efficient models perform like larger ones.

### Success Criteria
- Combined optimizations improve the Q4_K_M Hit@5 score by at least +10%, closing any gap with the Q8 model.

---

## Implementation

### 9.1 Script: `src/benchmarks/experiments.py`

```python
"""Experiments A1–A3: GGUF Quantization, Sampling Rate, Caption Style.

All experiments run CPU-only via llama.cpp to simulate mobile ARM.

Usage:
    uv run python src/benchmarks/experiments.py --experiment a1
    uv run python src/benchmarks/experiments.py --experiment a2 --video test_video.mp4
    uv run python src/benchmarks/experiments.py --experiment a3 --video test_video.mp4
    uv run python src/benchmarks/experiments.py --all --video test_video.mp4
"""
```

### 9.2 Taskfile Entry

```yaml
experiment:
  desc: Run vision experiments A1-A3 (CPU-only, mobile simulation)
  cmd: uv run python src/benchmarks/experiments.py --all --video test_video.mp4
```

## Verification
- [ ] All experiments run CPU-only (verify in output)
- [ ] Each experiment produces a formatted comparison table
- [ ] Results saved to `data/experiment_results.json`
- [ ] GGUF file sizes and RAM measurements are included (not just quality scores)

## Files Changed
- [NEW] `src/benchmarks/experiments.py`
- [MODIFY] `Taskfile.yml` — add `experiment` task

## Dependencies
- Step 04 (captioner via llama.cpp)
- Step 06 (memory integration — for A2 and A3)
- Multiple GGUF quantization variants downloaded (for A1)
- A test video file

## Common Issues
- A1 requires downloading multiple GGUF variants of the same model (Q8, Q5_K_M, Q4_K_M, Q4_0). Total disk space: ~5–8GB for all variants. Can delete after experiment.
- If the VLM model only has one GGUF variant available, A1 scope reduces to "whatever variants exist." Document this honestly.
