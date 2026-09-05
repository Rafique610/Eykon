"""Assistant feature module: prompt construction and local LLM generation."""

from src.assistant.helpers import check_model_available, get_model_status
from src.assistant.llm import generate_answer, get_engine, resolve_model_path
from src.assistant.prompt import build_rag_prompt

__all__ = [
    "build_rag_prompt",
    "check_model_available",
    "generate_answer",
    "get_engine",
    "get_model_status",
    "resolve_model_path",
]

