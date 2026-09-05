"""Assistant feature module: prompt construction and local LLM generation."""

from src.assistant.llm import generate_answer, get_engine, resolve_model_path
from src.assistant.prompt import build_rag_prompt

__all__ = [
    "build_rag_prompt",
    "generate_answer",
    "get_engine",
    "resolve_model_path",
]

