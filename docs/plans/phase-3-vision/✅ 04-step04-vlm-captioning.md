# Step 04 — VLM Captioning Module (llama.cpp Backend)

## What
Build `src/vision/captioner.py` — a module that takes a PIL Image and produces a text caption using a local VLM running through **llama.cpp** (not HuggingFace Transformers). This is the "eyes" of the system and uses the exact same inference engine that will run on mobile.

## Why
This module is the core differentiator of Phase 3. By using `llama-cpp-python` as the runtime, we guarantee that:
1. The model format (GGUF) is identical on laptop and phone
2. The inference engine (llama.cpp C/C++) is the same — on Android it compiles via NDK, on laptop via Python bindings
3. Performance characteristics (CPU inference, memory usage) are representative of mobile
4. We can swap VLM models (Moondream2 → SmolVLM → LLaVA-Phi) without changing any other code

## How to Implement

### 4.1 Module Structure

```
src/vision/
├── __init__.py      (updated)
├── extractor.py     (from Step 03)
├── captioner.py     ← this step (Dual backend: LiteRT-LM + llama.cpp)
```

### 4.2 `src/vision/captioner.py`

```python
"""VLM-based image captioning.
Primary backend: LiteRT-LM (reusing Gemma 4 E2B).
Fallback/Benchmark backend: llama.cpp (for Moondream2/PaliGemma).
"""
from pathlib import Path
from PIL import Image
from src.config import Settings
from src.assistant.llm import get_engine  # Existing LiteRT-LM engine

_LLAMA_CACHE = None

def get_vlm():
    """Get the appropriate VLM engine based on config.
    If using Gemma 4 (shared model), returns the existing LiteRT-LM engine.
    If using dedicated VLM (Moondream2), loads via llama.cpp.
    """
    settings = Settings()
    
    # Primary: Shared Model Architecture
    if settings.VLM_USE_SHARED_GEMMA:
        return get_engine()  # Zero extra RAM!
        
    # Fallback/Benchmark: llama.cpp
    global _LLAMA_CACHE
    if _LLAMA_CACHE is not None:
        return _LLAMA_CACHE

    from llama_cpp import Llama
    _LLAMA_CACHE = Llama(
        model_path=str(settings.VLM_MODEL_PATH),
        n_ctx=settings.VLM_CONTEXT_SIZE,
        n_gpu_layers=0,  # CPU-only for mobile sim
    )
    return _LLAMA_CACHE


def caption_image(
    image: Image.Image,
    prompt: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Generate a text caption for a single PIL image.
    Routes to either LiteRT-LM or llama.cpp based on active engine.
    """
    ...


def caption_images_batch(
    images: list[Image.Image],
    prompt: str | None = None,
    max_tokens: int | None = None,
) -> list[str]:
    """Caption multiple images sequentially.
    
    llama.cpp processes one image at a time (no batch parallelism on CPU).
    This mirrors mobile behavior where we process frames sequentially.
    """
    ...
```

### 4.3 Key Implementation Details

1. **Dual Backend Routing:** The captioner checks `VLM_USE_SHARED_GEMMA`. If true, it attempts to pass the image to the already-loaded Gemma 4 E2B via LiteRT-LM. This proves the "0MB extra RAM" architecture.
2. **llama.cpp multimodal API:** For benchmarking the alternatives (Moondream2/PaliGemma), it uses `llama-cpp-python`'s llava handler on CPU-only.
3. **Graceful Degradation:** If Gemma 4 rejects the image input (i.e., this specific Gemma variant lacks vision weights), the system gracefully falls back to Moondream2 via llama.cpp.

### 4.4 Update `src/vision/__init__.py`

Add exports for `caption_image`, `caption_images_batch`, `get_vlm`.

## Verification
- [ ] `caption_image(some_pil_image)` returns a non-empty string describing the image
- [ ] Caption is relevant to the image content (manual human check on 5 test images)
- [ ] Model loads via llama.cpp on **CPU-only** (verify `n_gpu_layers=0`)
- [ ] Single image captioning completes (may take 5–15s on CPU — that's expected and mirrors mobile)
- [ ] Calling `caption_image` twice reuses the cached model (no reload)
- [ ] RAM usage after model load is < 2GB (for Q4 model)

### Terminal Test Command
```bash
uv run python -c "
import psutil, os
from PIL import Image
from src.vision.captioner import caption_image

# Measure RAM before
proc = psutil.Process(os.getpid())
ram_before = proc.memory_info().rss / 1024 / 1024

img = Image.new('RGB', (384, 384), color='red')
result = caption_image(img)

ram_after = proc.memory_info().rss / 1024 / 1024
print(f'Caption: {result}')
print(f'RAM: {ram_before:.0f}MB → {ram_after:.0f}MB (model cost: {ram_after - ram_before:.0f}MB)')
"
```

## Files Changed
- [NEW] `src/vision/captioner.py`
- [MODIFY] `src/vision/__init__.py` — add captioner exports

## Dependencies
- Step 02 (llama-cpp-python must be installed, GGUF model must be downloaded)
- Step 03 (extractor provides the images, but captioner can be tested independently)

## Common Issues
- **Multimodal support varies by model:** Not all GGUF models support llama.cpp's multimodal handler. Moondream2 is relatively new to the GGUF ecosystem. If it doesn't work, SmolVLM and LLaVA-Phi are proven alternatives.
- **CPU inference is slow:** Expect 5–15 seconds per frame on laptop CPU. On mobile ARM, expect 10–30 seconds. This is expected and documented as a KPI.
- **Context size:** Vision models use a large chunk of context for the image tokens. Set `n_ctx=2048` minimum.
- **llama-cpp-python version:** Multimodal support was added in recent versions. Ensure ≥0.3.0.
