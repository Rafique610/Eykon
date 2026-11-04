"""Sustained processing soak test — thermal and memory stability.

Runs the full pipeline on a video for N minutes, sampling system metrics
every 10 seconds. Produces a time-series JSON and summary.

Usage:
    uv run python src/benchmarks/soak_test.py --video data/video1.mp4 --duration 30
"""
import argparse
import base64
import json
import os
import sys
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import psutil
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler

# Ensure project root is on sys.path so 'src' can be imported
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vision.extractor import extract_frames


# Use the winning mobile-tier model from A1
MODEL_PATH = "models/smolvlm/500M/SmolVLM-500M-Instruct-Q8_0.gguf"
MMPROJ_PATH = "models/smolvlm/500M/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf"
PROMPT = "Describe what you see in this image in one detailed sentence."

# Shared state for the monitor thread
monitor_running = True
metrics_samples: list[dict[str, Any]] = []


def _encode(img) -> str:
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def _get_cpu_temp() -> float | None:
    # Attempt to get CPU temp (often fails on Windows without Admin/WMI or specific hardware)
    try:
        temps = psutil.sensors_temperatures()
        if temps and 'coretemp' in temps:
            return float(temps['coretemp'][0].current)
    except Exception:
        pass
    return None


def monitor_thread(start_time: float, interval: int = 10):
    """Background thread to poll system resources every `interval` seconds."""
    proc = psutil.Process()
    # prime the cpu_percent counter
    psutil.cpu_percent(interval=None)
    
    while monitor_running:
        elapsed = time.time() - start_time
        ram_mb = proc.memory_info().rss / 1024 / 1024
        sys_ram_pct = psutil.virtual_memory().percent
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_temp = _get_cpu_temp()
        
        sample = {
            "elapsed_s": round(elapsed),
            "cpu_pct": cpu_pct,
            "ram_mb": round(ram_mb),
            "sys_ram_pct": sys_ram_pct,
            "cpu_temp_c": cpu_temp
        }
        metrics_samples.append(sample)
        
        # Sleep in small chunks so we can exit quickly when monitor_running becomes False
        for _ in range(interval * 2):
            if not monitor_running:
                break
            time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Run 30-minute VLM soak test.")
    parser.add_argument("--video", type=str, default="data/video1.mp4", help="Video to loop.")
    parser.add_argument("--duration", type=float, default=30.0, help="Duration in minutes.")
    args = parser.parse_args()

    if not Path(MODEL_PATH).exists() or not Path(MMPROJ_PATH).exists():
        print(f"[ERROR] SmolVLM Q8 model not found at {MODEL_PATH}")
        print("Run Experiment A1 first to download it.")
        sys.exit(1)

    print(f"\n--- Sustained Soak Test ({args.duration} minutes) ---")
    print(f"Video: {args.video}")
    print(f"Model: {MODEL_PATH} (CPU-only)")
    
    frames = extract_frames(args.video, interval_seconds=5.0)
    if not frames:
        print("[ERROR] No frames extracted.")
        sys.exit(1)
        
    print(f"Extracted {len(frames)} frames. Will loop continuously.\n")

    # Load Model
    print("Loading VLM...")
    handler = Llava15ChatHandler(clip_model_path=MMPROJ_PATH)
    vlm = Llama(model_path=MODEL_PATH, chat_handler=handler,
                n_ctx=2048, n_gpu_layers=0, verbose=False)
    
    duration_secs = args.duration * 60.0
    start_time = time.time()
    
    global monitor_running
    monitor_running = True
    monitor = threading.Thread(target=monitor_thread, args=(start_time, 10))
    monitor.start()

    frames_processed = 0
    latencies = []
    
    try:
        print(f"Starting test at {time.strftime('%H:%M:%S')}... Press Ctrl+C to stop early.\n")
        frame_idx = 0
        
        while (time.time() - start_time) < duration_secs:
            frame = frames[frame_idx % len(frames)]
            img_b64 = _encode(frame.image)
            
            t0 = time.perf_counter()
            _ = vlm.create_chat_completion(
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": PROMPT},
                ]}],
                max_tokens=64, # Cap slightly lower for raw throughput testing
            )
            lat = time.perf_counter() - t0
            latencies.append(lat)
            
            frames_processed += 1
            frame_idx += 1
            
            elapsed = time.time() - start_time
            if frames_processed % 5 == 0:
                print(f"[Elapsed: {elapsed/60:.1f}m / {args.duration}m] "
                      f"Frames: {frames_processed} | Last latency: {lat:.1f}s")
                      
    except KeyboardInterrupt:
        print("\n[!] Soak test interrupted by user. Generating summary for elapsed time.")
    except MemoryError:
        print("\n[!] OOM EVENT TRIGGERED.")
    finally:
        monitor_running = False
        monitor.join()

    # Generate Summary
    if not latencies:
        print("No frames processed.")
        sys.exit(0)
        
    actual_duration = time.time() - start_time
    peak_ram = max((s["ram_mb"] for s in metrics_samples), default=0)
    peak_cpu = max((s["cpu_pct"] for s in metrics_samples), default=0)
    
    # Drift: compare first 10 frames to last 10 frames
    first_10 = np.mean(latencies[:10]) if len(latencies) >= 10 else np.mean(latencies)
    last_10 = np.mean(latencies[-10:]) if len(latencies) >= 10 else np.mean(latencies)
    drift_pct = ((last_10 - first_10) / first_10) * 100 if first_10 > 0 else 0
    
    summary = {
        "duration_minutes": round(actual_duration / 60, 2),
        "total_frames_processed": frames_processed,
        "peak_ram_mb": peak_ram,
        "peak_cpu_pct": peak_cpu,
        "avg_caption_latency_s": round(float(np.mean(latencies)), 2),
        "latency_drift_pct": round(float(drift_pct), 1)
    }
    
    results = {
        "config": {"video": args.video, "target_duration_minutes": args.duration, "interval": 5},
        "samples": metrics_samples,
        "summary": summary
    }
    
    os.makedirs("data", exist_ok=True)
    with open("data/soak_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n── Soak Test Summary ──────────────────────────")
    print(f"Duration:           {summary['duration_minutes']} min")
    print(f"Frames Processed:   {frames_processed}")
    print(f"Peak RAM:           {peak_ram:,} MB")
    print(f"Peak CPU Usage:     {peak_cpu}%")
    print(f"Avg Latency:        {summary['avg_caption_latency_s']}s / frame")
    
    drift_sign = "+" if drift_pct >= 0 else ""
    drift_verdict = "Thermal throttle detected!" if drift_pct > 25 else "Acceptable"
    print(f"Latency Drift:      {drift_sign}{summary['latency_drift_pct']}% ({drift_verdict})")
    print("───────────────────────────────────────────────")
    print("Results saved to data/soak_test_results.json\n")


if __name__ == "__main__":
    main()
