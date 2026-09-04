# Persistent Memory App

A local-first personal memory app. Store details about your life (notes, facts, events, preferences), and query them using natural-language questions with locally-grounded retrieval-augmented generation (RAG).

> 🚧 **Status:** Prototype Phase 1 — Steps 01 (Setup), 02 (Storage Layer), and 04 (Embedding Wrapper) completed & verified.

## Architecture

Built using a **feature-based file structure**:
- `src/memories/`: 
  - `models.py`: Memory data schema (`MemoryRecord`).
  - `database.py`: SQLite persistence and table schema initialization.
  - `repository.py`: CRUD operations for memory records.
  - `embedder.py`: Local `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 512 tokens, 384-dim) wrapper with unit-length normalization.
- `src/assistant/`: Question-answering prompt builder and Ollama local LLM generation.
- `src/ui/`: Streamlit web interface.
- `src/config.py`: Central Pydantic settings (`BaseSettings` backed by `.env` with `MEMORY_` prefix).
- `data/memories.db`: Local embedded SQLite database.

## Quick Start

### 1. Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- [Ollama](https://ollama.ai) (for local LLM generation in Step 06+)

### 2. Install Dependencies
```bash
uv sync
```

### 3. Verify Setup, Storage, and Embedder
```bash
# Verify configuration
uv run python -c "from src.config import Settings; print(Settings())"

# Test SQLite storage layer
task test

# Verify local embedder
uv run python -c "from src.memories import Embedder; emb = Embedder(); print('Embedder OK | Dim:', len(emb.embed('test')))"
```

### 4. Inspect Database
The database is stored locally at `data/memories.db`. You can view and query it with:
- **VS Code Extension:** SQLite Viewer (by Florian Klampfer)
- **Dedicated GUI:** [DB Browser for SQLite](https://sqlitebrowser.org/) (recommended)
- **Universal GUI:** DBeaver (connect via SQLite driver pointing to `data/memories.db`)

### 5. Run the App (Coming in Step 07)
```bash
uv run streamlit run src/ui/app.py
# or
task run
```
