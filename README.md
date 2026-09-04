# Persistent Memory App

A local-first personal memory app. Store details about your life (notes, facts, events, preferences), and query them using natural-language questions with locally-grounded retrieval-augmented generation (RAG).

> 🚧 **Status:** Prototype in active development (Phase 1). See `PROJECT_SPEC.md` and `docs/plans/` for full architecture and step-by-step plans.

## Architecture

Built using a **feature-based file structure**:
- `src/memories/`: Memory models, SQLite persistence, text capture, vector embedding, and similarity search.
- `src/assistant/`: Question-answering prompt builder and Ollama local LLM generation.
- `src/ui/`: Streamlit web interface.
- `src/config.py`: Central Pydantic settings.

## Quick Start

### 1. Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- [Ollama](https://ollama.ai) (for local LLM generation in Step 06+)

### 2. Install Dependencies
```bash
uv sync
```

### 3. Verify Setup
```bash
uv run python -c "from src.config import Settings; print(Settings())"
```

### 4. Run the App (Once UI is built)
```bash
uv run streamlit run src/ui/app.py
# or
uv run python main.py
```
