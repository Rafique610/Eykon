# Step 08 — Benchmark Suite: Mobile-Relevant VLM Performance Metrics

## What
Build `src/benchmarks/vision_bench.py` — a benchmark script that measures KPIs **under mobile-simulated constraints** (CPU-only inference, RAM budget cap, GGUF model format). These are the exact numbers the panel asked for.

## Why
The panel stated: *"Students must have a tangible plan for deploying the model on mobile devices with KPIs to assess model efficiency in terms of utility and energy consumption."* This step produces those numbers using the exact same runtime and model format that will run on the phone.

## How to Implement

### 8.1 KPIs to Measure (All Mobile-Relevant)

| KPI | Unit | How Measured | Why Panel Cares |
|---|---|---|---|
| **VLM Load Time (CPU)** | seconds | Time from `get_vlm()` to model ready, CPU-only | How long does the app take to start on a phone? |
| **Per-Frame Caption Latency (CPU)** | seconds/frame | Time to caption one image, CPU-only | Can it process frames faster than they arrive? |
| **Throughput** | frames/minute | 60 / average_latency | Real-time viability |
| **Model RAM Footprint** | MB | `psutil.Process().memory_info().rss` delta before/after load | Does it fit in phone memory alongside the OS? |
| **Peak Process RAM** | MB | Max RSS during a batch of 20 frames | Will Android OOM-kill the app? |
| **Combined Model RAM** | MB | VLM + Embedding model loaded simultaneously | Total AI memory cost on phone |
| **CPU Utilization** | % | `psutil.cpu_percent()` averaged over processing | Battery drain indicator |
| **Caption Length** | tokens | Average token count of generated captions | Affects embedding quality and storage |
| **GGUF Model Size on Disk** | MB | File size of the .gguf file | Phone storage cost |
| **Storage Growth Rate** | KB/min of video | DB size increase per minute of processed video | How much phone storage per hour of use? |
| **Deduplication Ratio** | % | % of frames discarded because they are >0.95 similar to previous frame | Prevents DB bloat when scene is static |
| **1-Year Est. Storage** | GB | (Storage Growth * 120 mins/day * 365) * (1 - Dedup Ratio) | Direct answer to panel's scalability question |
| **Tokens Per Second (TPS)** | tok/s | Output tokens / inference time | Standard LLM performance metric |

### 8.2 Mobile Budget Compliance Check

After all benchmarks, print a **pass/fail checklist** against mobile budgets:

```
── Mobile Deployment Readiness ─────────────────
  [✅] Model size on disk       987 MB   ≤ 2,000 MB
  [✅] Model RAM footprint    1,204 MB   ≤ 2,000 MB
  [✅] Combined AI RAM        1,588 MB   ≤ 4,000 MB
  [⚠️] Per-frame latency      8.3s       ≤ 5.0s (WARN: 1.7x over budget)
  [✅] Storage growth rate      2.1 KB/min ≤ 10 KB/min
  [✅] Peak process RAM       1,847 MB   ≤ 4,000 MB
─────────────────────────────────────────────────
  VERDICT: 5/6 passed, 1 warning
  NOTE: Latency exceeds 5s target on x86 CPU. Expected ARM mobile
        latency: ~12-25s (2-3x slower). Consider larger sampling
        interval or smaller model for real-time use.
```

### 8.3 Mobile Latency Extrapolation

Since we can't run ARM on a laptop, we document an **extrapolation factor:**
- x86 laptop CPU is typically 2–3x faster than Snapdragon 8 Gen 2 for ML workloads
- We multiply laptop CPU latency by 2.5x to estimate mobile latency
- This is documented with citations in the re-defense report

### 8.4 Output Format

```
══════════════════════════════════════════════════════════
   VLM Pipeline Benchmark (Mobile Simulation — CPU Only)
══════════════════════════════════════════════════════════

  Model: moondream2-Q4_K_M.gguf (987 MB)
  Runtime: llama.cpp (CPU-only, n_gpu_layers=0)
  Frame Interval: 5.0s
  Test Frames: 20

  ── Model Loading ──────────────────────────────────────
  Load Time (CPU):     4.2s
  Model RAM Cost:      1,204 MB
  GGUF Size on Disk:   987 MB

  ── Captioning (CPU-only) ─────────────────────────────
  Avg Latency:         8.3s/frame
  Min / Max:           6.1s / 11.2s
  P95 Latency:         10.8s
  Throughput:           7.2 frames/min
  Tokens/Second:       15.4 tok/s
  Avg Caption Length:   24 tokens

  ── Full Pipeline (Extract + Caption + Embed + Store) ─
  Per Frame:           8.7s (caption: 8.3s, embed: 12ms, store: 0.8ms)
  Extract overhead:    negligible (<1ms/frame)

  ── Resource Footprint ────────────────────────────────
  Peak Process RAM:    1,847 MB
  Combined AI RAM:     1,588 MB (VLM: 1,204 + Embedder: 384)
  Avg CPU:             78%
  Raw Storage Growth:  2.1 KB/min of video
  Dedup Savings:       82% (Static scenes discarded)
  Optimized Storage:   0.38 KB/min of video

  ── Mobile Extrapolation (×2.5 ARM factor) ────────────
  Est. Mobile Latency: ~20.8s/frame
  Est. Mobile Throughput: ~2.9 frames/min
  1-Year Est. Storage: ~312 MB (based on 2 hrs/day + dedup)
  Recommendation: Use 10s frame interval on mobile

══════════════════════════════════════════════════════════
```

### 8.5 Taskfile Entry

```yaml
benchmark-vision:
  desc: Run VLM pipeline benchmark (CPU-only, mobile simulation)
  cmd: uv run python src/benchmarks/vision_bench.py --video test_video.mp4
```

## Verification
- [ ] Benchmark runs CPU-only (verify `n_gpu_layers=0` in output)
- [ ] All 12 KPIs are populated with real measured values
- [ ] Mobile budget compliance checklist is printed
- [ ] Mobile latency extrapolation is calculated and documented
- [ ] JSON results saved to `data/vision_benchmark_results.json`
- [ ] Results are reproducible (within ±15% variance across runs)

## Files Changed
- [NEW] `src/benchmarks/vision_bench.py`
- [MODIFY] `Taskfile.yml` — add `benchmark-vision` task

## Dependencies
- Step 05 (process_video)
- Step 06 (memory integration — for full pipeline benchmark)

## Common Issues
- CPU-only inference is intentionally slow. 5–15s per frame is expected and correct for mobile simulation.
- First run after model download is slower (disk cache cold). Run twice, use second run's numbers.
- `psutil.cpu_percent()` needs `interval=0.5` for accurate readings.
