"""VLM-based image captioning."""
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image
from huggingface_hub import hf_hub_download

from src.config import Settings

_LLAMA_CACHE = None

def get_vlm():
    settings = Settings()
    
    if getattr(settings, "VLM_USE_SHARED_GEMMA", True):
        from src.assistant.llm import get_engine
        return get_engine()
        
    global _LLAMA_CACHE
    if _LLAMA_CACHE is not None:
        return _LLAMA_CACHE

    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler

    model_path = settings.VLM_MODEL_PATH
    if not model_path:
        model_path = hf_hub_download(settings.VLM_MODEL_REPO, settings.VLM_MODEL_FILE, local_dir="models/smolvlm/500M")
        
    mmproj_path = getattr(settings, "VLM_MMPROJ_FILE", None)
    if mmproj_path and not Path(mmproj_path).exists():
        mmproj_path = hf_hub_download(settings.VLM_MODEL_REPO, mmproj_path, local_dir="models/smolvlm/500M")

    chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path) if mmproj_path else None
    
    _LLAMA_CACHE = Llama(
        model_path=model_path,
        chat_handler=chat_handler,
        n_ctx=settings.VLM_CONTEXT_SIZE,
        n_gpu_layers=settings.VLM_N_GPU_LAYERS,
        verbose=False
    )
    return _LLAMA_CACHE


def caption_image(
    image: Image.Image,
    prompt: str | None = None,
    max_tokens: int | None = None,
) -> str:
    settings = Settings()
    prompt = prompt or settings.CAPTION_PROMPT
    max_tokens = max_tokens or settings.CAPTION_MAX_TOKENS
        
    if getattr(settings, "VLM_USE_SHARED_GEMMA", True):
        import tempfile
        import os
        engine = get_vlm()
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            image.convert("RGB").save(tmp.name, format="JPEG")
            tmp_path = tmp.name
            
        try:
            import litert_lm
            sampler = litert_lm.SamplerConfig(temperature=0.0)
            conv = engine.create_conversation(sampler_config=sampler)
            
            # Ensure anti-repetition instruction is present
            safe_prompt = prompt if "repeat" in prompt.lower() else f"{prompt}\nBe concise and do not repeat words or phrases."
            
            res = conv.send_message({
                "role": "user",
                "content": [
                    {"type": "image", "path": tmp_path},
                    {"type": "text", "text": safe_prompt}
                ]
            }, max_output_tokens=max_tokens)
            
            # LiteRT-LM returns content which can be a dict/list
            if isinstance(res, dict):
                content = res.get("content", [])
                if isinstance(content, list):
                    return "".join(i.get("text", "") for i in content if isinstance(i, dict)).strip()
                return str(content).strip()
            return str(res).strip()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
    vlm = get_vlm()
    
    buffered = BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    res = vlm.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }
        ],
        max_tokens=max_tokens,
        temperature=0.2,
        repeat_penalty=1.2,
    )
    return res["choices"][0]["message"]["content"]


def caption_images_batch(
    images: list[Image.Image],
    prompt: str | None = None,
    max_tokens: int | None = None,
) -> list[str]:
    return [caption_image(img, prompt, max_tokens) for img in images]
