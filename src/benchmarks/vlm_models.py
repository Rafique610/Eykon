"""The models vlm_bench.py compares. Each load() returns a function: picture file in, caption out.

LiteRT-LM models (the runtime the phone app already has) are run with the same file the phone
would use. The others run with Hugging Face transformers on the laptop only, to see first
whether they are worth porting.
"""
from pathlib import Path

from huggingface_hub import hf_hub_download

LITERT = {  # name: (repository, file)
    "gemma4_e2b": (None, "models/gemma-4-E2B-it.litertlm"),
    "qwen2vl_2b": ("litert-community/Qwen2-VL-2B", "Qwen2-VL-2B.litertlm"),
    "lfm25vl_450m": ("litert-community/LFM2.5-VL-450M", "LFM2.5-VL-450M_int4_fixB.litertlm"),  # the plain int4 file shows the model only the top quarter of the picture on LiteRT-LM 0.16 and 0.17 (its model card)
    "lfm25vl_16b": ("litert-community/LFM2.5-VL-1.6B", "LFM2.5-VL-1.6B_int4_fixB.litertlm"),
}
TRANSFORMERS = {
    "smolvlm_256m": "HuggingFaceTB/SmolVLM-256M-Instruct",
    "smolvlm_500m": "HuggingFaceTB/SmolVLM-500M-Instruct",
    "florence2_base": "florence-community/Florence-2-base",
}


def load(name: str, prompt: str, max_tokens: int):
    if name in LITERT:
        return _litert(name, prompt, max_tokens)
    if name.startswith("florence2"):
        return _florence(TRANSFORMERS[name], max_tokens)
    return _transformers_chat(TRANSFORMERS[name], prompt, max_tokens)


def _litert(name: str, prompt: str, max_tokens: int):
    import litert_lm

    repo, file = LITERT[name]
    path = file if repo is None else hf_hub_download(repo, file)
    engine = litert_lm.Engine(model_path=str(path), backend=litert_lm.Backend.CPU(), vision_backend=litert_lm.Backend.CPU())

    def caption(picture: Path) -> str:
        conversation = engine.create_conversation(sampler_config=litert_lm.SamplerConfig(temperature=0.0))
        reply = conversation.send_message(
            {"role": "user", "content": [{"type": "image", "path": str(picture)}, {"type": "text", "text": prompt}]},
            max_output_tokens=max_tokens,
        )
        content = reply.get("content", []) if isinstance(reply, dict) else reply
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
        return str(content).strip()

    return caption


def _transformers_chat(repo: str, prompt: str, max_tokens: int):
    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    processor = AutoProcessor.from_pretrained(repo)
    model = AutoModelForImageTextToText.from_pretrained(repo, torch_dtype=torch.float32).eval()
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
    text = processor.apply_chat_template(messages, add_generation_prompt=True)

    def caption(picture: Path) -> str:
        inputs = processor(text=text, images=[Image.open(picture).convert("RGB")], return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
        return processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()

    return caption


def _florence(repo: str, max_tokens: int):
    """Florence-2 takes task words instead of a free prompt: a detailed caption, plus the names of
    the things it detects, joined into one text so it is scored like the others."""
    import torch
    from PIL import Image
    from transformers import AutoProcessor, Florence2ForConditionalGeneration

    processor = AutoProcessor.from_pretrained(repo)
    model = Florence2ForConditionalGeneration.from_pretrained(repo, torch_dtype=torch.float32).eval()

    def run(image, task: str):
        inputs = processor(text=task, images=image, return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False, num_beams=1)
        raw = processor.batch_decode(out, skip_special_tokens=False)[0]
        return processor.post_process_generation(raw, task=task, image_size=image.size)[task]

    def caption(picture: Path) -> str:
        image = Image.open(picture).convert("RGB")
        text = run(image, "<DETAILED_CAPTION>")
        things = sorted(set(run(image, "<OD>").get("labels", [])))
        return f"{text.strip()} Objects: {', '.join(things)}." if things else text.strip()

    return caption
