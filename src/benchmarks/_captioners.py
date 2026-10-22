"""VLM captioning backends for A6: llama.cpp (SmolVLM / Moondream2) and HF Transformers (Gemma 4)."""
from __future__ import annotations

import base64
import gc
import time
from io import BytesIO

import psutil

_ram = lambda: psutil.Process().memory_info().rss / 1024 / 1024  # noqa: E731

CAPTION_PROMPT = "Describe what you see in this image in one detailed sentence."

A6_MODELS: list[dict] = [
    {
        "label": "SmolVLM-500M-Q8_0",
        "type": "llama",
        "model": "models/smolvlm/500M/SmolVLM-500M-Instruct-Q8_0.gguf",
        "mmproj": "models/smolvlm/500M/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf",
    },
    {
        "label": "Moondream2-INT8",
        "type": "llama",
        "hf_repo": "vikhyatk/moondream2",
        "hf_model_file": "moondream2-int8.gguf",
        "hf_mmproj_file": "mmproj-moondream2-f16.gguf",
    },
    {
        "label": "Gemma4-E2B (Shared)",
        "type": "litert",
        "model": "models/gemma-4-E2B-it.litertlm",
    },
]


def _b64(img) -> str:
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def caption_with_llama(
    cfg: dict, frames: list, n: int
) -> tuple[list[str], list[float], float]:
    """Caption up to n frames using llama.cpp (SmolVLM or Moondream2).

    Returns (captions, per-frame latencies, ram_cost_mb).
    """
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler

    model_path = cfg.get("model", "")
    mmproj_path = cfg.get("mmproj", "")
    if cfg.get("hf_repo"):
        from huggingface_hub import hf_hub_download
        model_path = hf_hub_download(cfg["hf_repo"], cfg["hf_model_file"])
        mmproj_path = hf_hub_download(cfg["hf_repo"], cfg["hf_mmproj_file"])

    r0 = _ram()
    handler = Llava15ChatHandler(clip_model_path=mmproj_path, verbose=False)
    vlm = Llama(model_path=model_path, chat_handler=handler,
                n_ctx=2048, n_gpu_layers=0, verbose=False)
    ram_mb = _ram() - r0

    captions, lats = [], []
    for f in frames[:n]:
        t0 = time.perf_counter()
        res = vlm.create_chat_completion(
            messages=[{"role": "user", "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{_b64(f.image)}"}},
                {"type": "text", "text": CAPTION_PROMPT},
            ]}],
            max_tokens=128,
        )
        lats.append(time.perf_counter() - t0)
        captions.append(res["choices"][0]["message"]["content"].strip())

    del vlm, handler
    gc.collect()
    return captions, lats, ram_mb


def caption_with_gemma4(
    model_path: str, frames: list, n: int
) -> tuple[list[str], list[float], float]:
    """Caption up to n frames using Gemma 4 E2B via litert_lm natively.
    Returns (captions, per-frame latencies, ram_cost_mb).
    """
    import litert_lm
    import tempfile
    import os

    r0 = _ram()
    try:
        engine = litert_lm.Engine(
            model_path=model_path,
            backend=litert_lm.Backend.CPU(),
            vision_backend=litert_lm.Backend.CPU()
        )
    except Exception as e:
        skip = f"SKIPPED (Failed to load litert_lm Engine): {e}"
        return [skip] * n, [0.0] * n, 0.0

    ram_mb = _ram() - r0
    captions, lats = [], []
    
    # litert_lm requires image paths (not raw bytes/PIL objects directly in the dict)
    for f in frames[:n]:
        # Save frame to a temporary file since litert_lm expects a path
        fd, temp_img_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        try:
            f.image.convert("RGB").save(temp_img_path, format="JPEG")
            
            conv = engine.create_conversation()
            msg = {
                "role": "user",
                "content": [
                    {"type": "image", "path": temp_img_path},
                    {"type": "text", "text": CAPTION_PROMPT},
                ],
            }
            
            t0 = time.perf_counter()
            res = conv.send_message(msg)
            lats.append(time.perf_counter() - t0)
            
            # Parse the response
            content = res.get("content", [])
            text_out = ""
            if isinstance(content, list):
                parts = [item.get("text", "") for item in content if isinstance(item, dict) and "text" in item]
                text_out = "".join(parts).strip()
            elif isinstance(content, str):
                text_out = content.strip()
            else:
                text_out = str(res).strip()
                
            captions.append(text_out)
        except Exception as e:
            captions.append(f"SKIPPED (litert_lm error): {e}")
            lats.append(0.0)
        finally:
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)

    del engine
    gc.collect()
    return captions, lats, ram_mb
