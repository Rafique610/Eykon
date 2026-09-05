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
    TOP_K: int = 5

