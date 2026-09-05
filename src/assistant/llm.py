from pathlib import Path
from typing import Any

from src.config import Settings
from src.memories.models import MemoryRecord
from src.assistant.prompt import build_rag_prompt

_ENGINE_CACHE: Any = None


def resolve_model_path() -> Path:
    """Resolve local path to the Gemma 4 LiteRT model file, or raise helpful error."""
    settings = Settings()
    if settings.LITERT_MODEL_PATH and Path(settings.LITERT_MODEL_PATH).exists():
        return Path(settings.LITERT_MODEL_PATH)

    # Check Hugging Face hub cache
    from huggingface_hub import try_to_load_from_cache
    cached = try_to_load_from_cache(
        repo_id=settings.LITERT_MODEL_REPO,
        filename=settings.LITERT_MODEL_FILE,
    )
    if isinstance(cached, str) and Path(cached).exists():
        return Path(cached)

    # Check local models directory
    for candidate in [Path("models") / settings.LITERT_MODEL_FILE, Path("data/models") / settings.LITERT_MODEL_FILE]:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Gemma 4 LiteRT model file '{settings.LITERT_MODEL_FILE}' not found locally. "
        f"Please run 'task pull-model' to download it (~2.4 GB) from {settings.LITERT_MODEL_REPO}."
    )


def get_engine(model_path: str | Path | None = None) -> Any:
    """Return a cached LiteRT-LM Engine instance."""
    global _ENGINE_CACHE
    if _ENGINE_CACHE is not None:
        return _ENGINE_CACHE

    import litert_lm
    resolved = str(model_path or resolve_model_path())
    _ENGINE_CACHE = litert_lm.Engine(model_path=resolved)
    return _ENGINE_CACHE


def generate_answer(
    question: str,
    context_memories: list[MemoryRecord],
    engine: Any | None = None,
    max_output_tokens: int = 256,
    temperature: float = 0.1,
) -> str:
    """Generate a factual answer grounded in retrieved memories using Gemma 4 LiteRT-LM."""
    prompt = build_rag_prompt(question, context_memories)

    try:
        if engine is None:
            engine = get_engine()

        import litert_lm
        sampler = litert_lm.SamplerConfig(temperature=temperature)
        conversation = engine.create_conversation(sampler_config=sampler)

        response = conversation.send_message(
            prompt,
            max_output_tokens=max_output_tokens,
        )
    except FileNotFoundError:
        raise  # Let the UI handle model-not-found specifically
    except Exception as exc:
        raise RuntimeError(
            f"LLM generation failed: {exc}. "
            "Make sure the model is downloaded ('task pull-model') and enough memory is available."
        ) from exc

    if isinstance(response, dict):
        content = response.get("content", [])
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and "text" in item
            ]
            if parts:
                return "".join(parts).strip()
        elif isinstance(content, str):
            return content.strip()

    return str(response).strip()
