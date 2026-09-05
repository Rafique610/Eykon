"""LLM health check utilities — model availability and status reporting."""

from src.assistant.llm import resolve_model_path


def check_model_available() -> bool:
    """Return True if the Gemma 4 LiteRT model file is found locally."""
    try:
        resolve_model_path()
        return True
    except FileNotFoundError:
        return False


def get_model_status() -> tuple[bool, str]:
    """Return (available, message) describing model readiness."""
    try:
        path = resolve_model_path()
        return True, f"Model ready ({path.name})"
    except FileNotFoundError as e:
        return False, str(e)
