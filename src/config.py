from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Persistent Memory App.
    
    All settings can be overridden using the MEMORY_ prefix in environment variables
    or via a .env file.
    """
    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma2:2b"
    LITERT_MODEL_REPO: str = "litert-community/gemma-4-E2B-it-litert-lm"
    LITERT_MODEL_FILE: str = "gemma-4-E2B-it.litertlm"
    LITERT_MODEL_PATH: str | None = None
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    DB_PATH: str = "data/memories.db"
    # RAG Settings
    TOP_K: int = 5
    POOL_K: int = 20  # Candidates retrieved from each method in hybrid search before fusion
    EXPAND_QUERY: bool = True  # Enable static concept expansion for semantic queries
    RERANK: bool = True  # Enable cross-encoder re-ranking for hybrid search

    # Vision / VLM Settings (mobile-compatible)
    VLM_MODEL_PATH: str | None = None
    VLM_MODEL_REPO: str = "ggml-org/SmolVLM-500M-Instruct-GGUF"
    VLM_MODEL_FILE: str = "SmolVLM-500M-Instruct-Q8_0.gguf"
    VLM_MMPROJ_FILE: str | None = "mmproj-SmolVLM-500M-Instruct-Q8_0.gguf"
    FRAME_INTERVAL_SECONDS: float = 5.0
    CAPTION_MAX_TOKENS: int = 300
    CAPTION_PROMPT: str = (
        "Describe this image thoroughly for visual memory storage:\n"
        "- State the room or setting and main surface.\n"
        "- List all visible objects, personal items, accessories, food, and containers.\n"
        "- Note their exact locations and spatial relationships (what is next to, behind, or on top of what).\n"
        "Be precise, factual, and do not repeat words."
    )
    VLM_N_GPU_LAYERS: int = 0
    VLM_CONTEXT_SIZE: int = 2048
    VLM_USE_SHARED_GEMMA: bool = True

    # Video memory (cheap-model pipeline, src/video_memory)
    video_dir: Path = Path("data/videos")
    video_image_dim: int = 512
    video_text_dim: int = 384
    video_audio_dim: int = 512
    video_max_mb: int = 500
    video_types: list[str] = ["mp4", "mov", "m4v", "avi"]

    # Perception, Option A: detector + place / action prompts (the phone holds the same values in OptionA.kt)
    detector_model: Path = Path("models/yolox_tiny.onnx")
    detector_url: str = "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_tiny.onnx"
    detector_conf: float = 0.35
    scene_prompt_min: float = 0.30
    scene_places: list[str] = [
        "a kitchen", "a hallway", "a bedroom", "a living room", "an office",
        "a classroom", "a street", "inside a car", "a shop",
    ]
    scene_actions: list[str] = [
        "picking something up", "putting something down", "typing on a laptop", "cooking",
        "walking", "talking to someone", "reading", "eating",
    ]
