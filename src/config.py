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
    VLM_MODEL_REPO: str = "moondream/moondream2-gguf"
    VLM_MODEL_FILE: str = "moondream2-text-model-f16.gguf"
    VLM_MMPROJ_FILE: str | None = "moondream2-mmproj-f16.gguf"
    FRAME_INTERVAL_SECONDS: float = 5.0
    CAPTION_MAX_TOKENS: int = 128
    CAPTION_PROMPT: str = "Describe what you see in this image in one detailed sentence."
    VLM_N_GPU_LAYERS: int = 0
    VLM_CONTEXT_SIZE: int = 2048
