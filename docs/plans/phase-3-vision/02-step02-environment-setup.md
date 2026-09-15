# Step 02 — Environment Setup & VLM Model Download (llama.cpp + GGUF)

## What
Install the Python dependencies needed for video processing and **mobile-compatible** VLM inference, download the VLM model in GGUF format, and add Taskfile entries.

## Why
We must use the **exact same inference runtime and model format** that will run on the phone. That means `llama.cpp` (not HuggingFace Transformers) and `.gguf` models (not PyTorch weights). The laptop is just the test bench — every tool choice must translate directly to Android.

## How to Implement

### 2.1 Add Dependencies to `pyproject.toml`

```toml
"opencv-python>=4.8.0",          # Frame extraction (→ MediaCodec on Android)
"llama-cpp-python>=0.3.0",       # llama.cpp Python bindings (→ llama.cpp NDK on Android)
"Pillow>=10.0.0",                # Image handling
"psutil>=5.9.0",                 # RAM/CPU monitoring for benchmarks
```

**NOT included (and why):**
- ❌ `transformers` — HuggingFace runtime doesn't exist on mobile
- ❌ `accelerate` — PyTorch-only, not mobile
- ❌ `bitsandbytes` — CUDA-only quantization, not GGUF
- ❌ `torch` — not needed; llama.cpp handles inference natively

### 2.2 Add VLM Config to `src/config.py`

Extend the `Settings` class with new fields:
```python
# Vision / VLM Settings (mobile-compatible)
VLM_MODEL_PATH: str | None = None                    # Path to .gguf model file
VLM_MODEL_REPO: str = "vikhyatk/moondream2"           # HF repo for GGUF download
VLM_MODEL_FILE: str = "moondream2-text-model-f16.gguf" # GGUF filename (will find exact name)
FRAME_INTERVAL_SECONDS: float = 5.0                    # 1 frame every N seconds
CAPTION_MAX_TOKENS: int = 128                          # Max tokens for VLM caption output
CAPTION_PROMPT: str = "Describe what you see in this image in one detailed sentence."
VLM_N_GPU_LAYERS: int = 0                              # 0 = CPU-only (mobile simulation)
VLM_CONTEXT_SIZE: int = 2048                           # Context window for VLM
```

**Key:** `VLM_N_GPU_LAYERS = 0` forces **CPU-only** inference by default. This simulates the mobile ARM CPU. We can override it for optional GPU comparison benchmarks.

### 2.3 Download GGUF Model

Moondream2 GGUF models are available from community quantizations on HuggingFace. We need to find the correct repo that provides `.gguf` format.

Research required during execution:
1. Search HuggingFace for `moondream2 gguf` — find the community quantization repo
2. Download the Q4_K_M variant (~1GB)
3. Store in `models/` directory (same pattern as the existing Gemma model)

### 2.4 Taskfile Entries

```yaml
pull-vlm:
  desc: Download Moondream2 GGUF model for video captioning (mobile-compatible format)
  cmd: uv run python -c "from huggingface_hub import hf_hub_download; ..."

check-vlm:
  desc: Verify VLM model is downloaded and llama.cpp can load it
  cmd: uv run python -c "from llama_cpp import Llama; ..."
```

### 2.5 Verify Installation

Quick smoke test:
```python
import cv2
import llama_cpp
from PIL import Image
import psutil
print("All mobile-compatible vision dependencies OK")
```

### 2.6 Verify llama-cpp-python Multimodal Support

llama.cpp supports multimodal (vision) models via the `llava` handler. We need to verify:
1. `llama-cpp-python` is built with multimodal support
2. It can load a vision GGUF model
3. It can accept an image + text prompt and return a caption

If Moondream2 GGUF doesn't have proper llava-compatible support in llama.cpp, we fall back to **SmolVLM** or **LLaVA-Phi** which have confirmed llama.cpp multimodal support.

## Verification
- [ ] `uv sync` completes without errors
- [ ] `llama-cpp-python` is installed and importable
- [ ] GGUF model file exists in `models/` directory
- [ ] `import cv2, llama_cpp, PIL, psutil` works
- [ ] `src/config.py` Settings includes VLM fields
- [ ] `task check-config` shows the new VLM settings
- [ ] llama.cpp can load the GGUF model on CPU-only

## Files Changed
- [MODIFY] `pyproject.toml` — add opencv-python, llama-cpp-python, Pillow, psutil
- [MODIFY] `src/config.py` — add VLM settings (mobile-compatible, CPU-only default)
- [MODIFY] `Taskfile.yml` — add `pull-vlm` and `check-vlm` tasks

## Dependencies
- None (first technical step)

## Common Issues
- `llama-cpp-python` on Windows may need Visual Studio Build Tools for compilation. Pre-built wheels are available from `pip install llama-cpp-python --prefer-binary`.
- Moondream2 may not have a ready-made GGUF with proper multimodal (llava) support. In that case, we switch to **SmolVLM (2B)** or **LLaVA-Phi (3B)** which have confirmed llama.cpp GGUF support. The captioner module's interface stays the same regardless.
- The exact GGUF repo/filename will be determined during execution by searching HuggingFace. The config defaults are placeholders.
