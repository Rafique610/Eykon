"""Experiment A1: SmolVLM model-size vs caption-quality comparison (3-way).

Loads 256M-Q8_0, 500M-Q8_0, and 500M-F16 sequentially on CPU-only inference
(n_gpu_layers=0) to simulate mobile ARM constraints. Measures disk size, RAM
footprint, load time, per-frame latency, tokens/second, and cosine similarity
of each variant vs the F16 baseline.
"""
import gc
import base64
import time
import numpy as np
import psutil
from io import BytesIO
from pathlib import Path

from src.memories import Embedder
from src.vision.extractor import extract_frames


VARIANTS = [
    {
        "label": "256M-Q8_0",
        "model":  "models/smolvlm/256M/SmolVLM-256M-Instruct-Q8_0.gguf",
        "mmproj": "models/smolvlm/256M/mmproj-SmolVLM-256M-Instruct-Q8_0.gguf",
    },
    {
        "label": "500M-Q8_0",
        "model":  "models/smolvlm/500M/SmolVLM-500M-Instruct-Q8_0.gguf",
        "mmproj": "models/smolvlm/500M/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf",
    },
    {
        "label": "500M-F16 (baseline)",
        "model":  "models/smolvlm/500M/SmolVLM-500M-Instruct-f16.gguf",
        "mmproj": "models/smolvlm/500M/mmproj-SmolVLM-500M-Instruct-f16.gguf",
    },
]

PROMPT = "Describe what you see in this image in one detailed sentence."
BASELINE = "500M-F16 (baseline)"


def _encode(img) -> str:
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def run_experiment_a1(video_path: str) -> list[dict]:
    """Run A1 and return a results table (list of dicts, one row per variant)."""
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler

    print("\n--- Experiment A1: SmolVLM Size vs Quality (3-way) ---")
    print("Variants: SmolVLM-256M-Q8_0 | 500M-Q8_0 | 500M-F16 (baseline)")
    print("Inference: CPU-only (mobile simulation)\n")

    frames = extract_frames(video_path, interval_seconds=1.0)[:10]
    print(f"Test frames: {len(frames)} (1s interval, capped at 10)")

    proc = psutil.Process()
    results_table: list[dict] = []
    all_captions: dict[str, list[str]] = {}

    for v in VARIANTS:
        label = v["label"]
        print(f"\n[{label}]")

        disk_mb = round(
            (Path(v["model"]).stat().st_size + Path(v["mmproj"]).stat().st_size) / 1024 / 1024
        )
        ram_before = proc.memory_info().rss / 1024 / 1024

        t0 = time.perf_counter()
        handler = Llava15ChatHandler(clip_model_path=v["mmproj"])
        vlm = Llama(model_path=v["model"], chat_handler=handler,
                    n_ctx=2048, n_gpu_layers=0, verbose=False)
        load_time = round(time.perf_counter() - t0, 1)
        ram_cost = round(proc.memory_info().rss / 1024 / 1024 - ram_before)

        latencies, token_counts, captions = [], [], []
        for frame in frames:
            img_b64 = _encode(frame.image)
            t1 = time.perf_counter()
            res = vlm.create_chat_completion(
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": PROMPT},
                ]}],
                max_tokens=128,
            )
            latencies.append(time.perf_counter() - t1)
            token_counts.append(res["usage"]["completion_tokens"])
            captions.append(res["choices"][0]["message"]["content"])

        all_captions[label] = captions
        avg_lat = float(np.mean(latencies))
        avg_tok = float(np.mean(token_counts))

        results_table.append({
            "Variant":     label,
            "Disk (MB)":   disk_mb,
            "RAM (MB)":    ram_cost,
            "Load (s)":    load_time,
            "Latency (s)": round(avg_lat, 1),
            "TPS":         round(avg_tok / avg_lat, 1),
            "Avg Tokens":  round(avg_tok),
            "Cosine Sim":  None,
        })
        print(f"  disk={disk_mb}MB  ram={ram_cost}MB  load={load_time}s  "
              f"latency={avg_lat:.1f}s  tps={avg_tok/avg_lat:.1f}")

        del vlm, handler
        gc.collect()

    # Cosine similarity vs F16 baseline
    # embed() returns unit-normalized vectors so cosine sim = dot product
    embedder = Embedder()
    base_embs = [embedder.embed(c) for c in all_captions[BASELINE]]

    for row in results_table:
        if row["Variant"] == BASELINE:
            row["Cosine Sim"] = 1.000
            continue
        sims = [
            float(np.dot(embedder.embed(c), b))
            for c, b in zip(all_captions[row["Variant"]], base_embs)
        ]
        row["Cosine Sim"] = round(float(np.mean(sims)), 3)

    print("\n| Variant | Disk (MB) | RAM (MB) | Load (s) | Latency (s) | TPS | Avg Tokens | Cosine Sim |")
    print("|---|---|---|---|---|---|---|---|")
    for r in results_table:
        print(f"| {r['Variant']} | {r['Disk (MB)']} | {r['RAM (MB)']} | {r['Load (s)']} | "
              f"{r['Latency (s)']} | {r['TPS']} | {r['Avg Tokens']} | {r['Cosine Sim']} |")

    return results_table
