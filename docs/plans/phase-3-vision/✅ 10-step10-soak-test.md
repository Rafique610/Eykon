# Step 10 — Experiment A4: Sustained Processing (Thermal/Memory Soak Test, CPU-Only)

## What
Run the VLM pipeline continuously for 30+ minutes **on CPU-only** (simulating mobile ARM) on a looped video while monitoring CPU temperature, RAM usage, and system stability. This is the "soak test" that proves the system survives the 2-hour use case on constrained hardware.

## Why
The panel specifically asked about *"thermal issues"* and *"compute"* for sustained use. By running CPU-only, we simulate the thermal pressure a phone's ARM chip would experience. This produces a time-series chart showing stability — or identifying exactly where it breaks.

## How to Implement

### 10.1 Monitoring Script: `src/benchmarks/soak_test.py`

```python
"""Sustained processing soak test — thermal and memory stability.

Runs the full pipeline on a video for N minutes, sampling system metrics
every 10 seconds. Produces a time-series JSON and summary.

Usage:
    uv run python src/benchmarks/soak_test.py --video test_video.mp4 --duration 30
    uv run python src/benchmarks/soak_test.py --video test_video.mp4 --duration 60 --loop
"""
```

### 10.2 Metrics Collected Every 10 Seconds

| Metric | Source | Unit |
|---|---|---|
| Elapsed time | `time.time()` | seconds |
| CPU utilization | `psutil.cpu_percent()` | % |
| CPU temperature | `psutil.sensors_temperatures()` (Linux) or WMI (Windows) | °C |
| RAM used by process | `psutil.Process().memory_info().rss` | MB |
| Total system RAM used | `psutil.virtual_memory().percent` | % |
| GPU temperature | `nvidia-smi` or `torch.cuda` (if available) | °C |
| GPU VRAM used | `torch.cuda.memory_allocated()` | MB |
| Frames processed so far | Counter | count |
| Current caption latency | Timer | seconds |

### 10.3 Output

1. **Time-series JSON:** `data/soak_test_results.json`
   ```json
   {
     "config": {"video": "...", "duration_minutes": 30, "interval": 5},
     "samples": [
       {"elapsed_s": 0, "cpu_pct": 12, "ram_mb": 1200, "gpu_temp_c": 45, ...},
       {"elapsed_s": 10, "cpu_pct": 67, "ram_mb": 1850, "gpu_temp_c": 62, ...},
       ...
     ],
     "summary": {
       "peak_ram_mb": 2341,
       "peak_cpu_pct": 89,
       "peak_gpu_temp_c": 78,
       "total_frames_processed": 360,
       "oom_events": 0,
       "thermal_throttle_events": 0,
       "avg_caption_latency_s": 2.1
     }
   }
   ```

2. **Console summary table:**
   ```
   ── 30-Minute Soak Test Summary ──────────────
   Duration:           30:00
   Frames Processed:   360
   OOM Events:         0
   Thermal Throttles:  0
   Peak RAM:           2,341 MB
   Peak GPU Temp:      78°C
   Avg Latency:        2.1s/frame (stable ±0.3s)
   Latency Drift:      +0.2s over 30 min (acceptable)
   ──────────────────────────────────────────────
   VERDICT: ✅ STABLE — No degradation detected
   ```

### 10.4 Key Implementation Details

1. **Looping:** If the test video is shorter than the desired duration, `--loop` restarts processing from the beginning. This simulates continuous operation.
2. **Latency drift detection:** Compare average latency in the first 5 minutes vs last 5 minutes. If the last 5 min is >50% slower, flag "thermal throttling detected."
3. **OOM detection:** Wrap the processing loop in a try/except. If an OOM occurs, log the timestamp and continue monitoring.
4. **CPU temperature on Windows:** Use `wmi` module or `psutil` (not all Windows machines expose temps). If unavailable, skip and note "temp monitoring not available."

### 10.5 Taskfile Entry

```yaml
soak-test:
  desc: Run 30-minute sustained VLM processing soak test
  cmd: uv run python src/benchmarks/soak_test.py --video test_video.mp4 --duration 30 --loop
```

## Verification
- [ ] Soak test runs for the full specified duration without crashing
- [ ] Time-series data is collected every 10 seconds
- [ ] Summary table is printed at the end
- [ ] JSON results are saved
- [ ] Latency drift is calculated and reported
- [ ] System remains responsive during the test (not frozen)

## Files Changed
- [NEW] `src/benchmarks/soak_test.py`
- [MODIFY] `Taskfile.yml` — add `soak-test` task

## Dependencies
- Step 05 (process_video)
- Step 08 (reuses measurement utilities)
- A test video (at least 5 minutes long, or use --loop with a shorter one)

## Common Issues
- Windows often does not expose CPU temperature via `psutil`. Use the `wmi` package as fallback, or skip temp reporting and rely on external monitoring (HWMonitor).
- If the laptop has no GPU, skip GPU metrics entirely and document "CPU-only run."
- Very long soak tests (>1 hour) may fill up disk if storing all memories. Use a separate throwaway DB.
