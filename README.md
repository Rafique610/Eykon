# Persistent Memory App

A local-first personal memory app. Store details about your life (notes, facts, events, preferences), and query them using natural-language questions with locally-grounded retrieval-augmented generation (RAG).

> 🚧 **Status:** Prototype Phase 1 — Steps 01 (Setup), 02 (Storage Layer), 04 (Embedding Wrapper), and 03 (Capture Layer) completed & verified.

## Architecture

Built using a **feature-based file structure**:
- `src/memories/`: 
  - `models.py`: Memory data schema (`MemoryRecord` with `metadata` support).
  - `database.py`: SQLite persistence and table schema initialization with idempotent `metadata` migration.
  - `repository.py`: CRUD operations for memory records (`save_memory`, `save_memories`, `get_all_memories`, `get_memory_by_id`).
  - `embedder.py`: Local `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 512 tokens, 384-dim) wrapper with token counting (`count_tokens`, `tokenize`, `decode_tokens`).
  - `service.py`: Text validation, token-bounded chunking (256 avg, 30-50 overlap, 400 ceiling), and `MemoryRecord` assembly (`create_memories_from_text`, `create_memory_from_text`).
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

### 3. Verify Setup, Storage, Embedder, and Capture Layer
```bash
# Verify configuration
uv run python -c "from src.config import Settings; print(Settings())"

# Test full pipeline (Config, Storage, Embedder, Chunking, Capture)
uv run python -c "from src.config import Settings; from src.memories import init_db, count_memories, Embedder, create_memories_from_text; init_db(); emb = Embedder(); recs = create_memories_from_text('Test memory chunking', emb); print('Pipeline OK | Count:', count_memories(), '| Chunks:', len(recs), '| Metadata:', recs[0].metadata)"

# Test Token Chunking & Metadata directly
uv run python -c "from src.memories import create_memories_from_text, Embedder; emb = Embedder(); text = 'Long note sample. ' * 45; recs = create_memories_from_text(text, emb); print(f'Split into {len(recs)} chunks:'); [print(f'  Chunk {r.metadata[\"chunk_index\"]}: {r.metadata}') for r in recs]"
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
