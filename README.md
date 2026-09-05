# Persistent Memory App

A local-first personal memory app. Store details about your life (notes, facts, events, preferences), and query them using natural-language questions with locally-grounded retrieval-augmented generation (RAG).

> ✅ **Status:** Phase 1 Complete — All 8 steps done: Setup, Storage, Embedder, Capture, Retrieval (Hybrid Search), Generation (Gemma 4 LiteRT-LM), Streamlit UI, and Integration Test & Polish.

## Architecture

Built using a **feature-based file structure**:
- `src/memories/`: 
  - `models.py`: Memory data schema (`MemoryRecord` with `metadata` support).
  - `database.py`: SQLite persistence, table schema, and `memories_fts` (FTS5) virtual table with sync triggers.
  - `repository.py`: CRUD operations for memory records (`save_memory`, `save_memories`, `get_all_memories`, `get_memory_by_id`).
  - `embedder.py`: Local `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 512 tokens, 384-dim) wrapper with token helpers.
  - `service.py`: Text validation, token-bounded chunking (256 avg, 30-50 overlap, 400 ceiling), and `MemoryRecord` assembly.
  - `search.py`: Hybrid search engine pooling top 5 from semantic cosine and top 5 from SQLite FTS5 BM25, prioritizing memories common to both, then filling with highest individual scores. Emits `SearchResult` objects with individual semantic, BM25, and fused RRF scores.
- `src/assistant/`: 
  - `prompt.py`: Factual RAG prompt formatting with strict anti-hallucination guard (`build_rag_prompt`).
  - `llm.py`: Google LiteRT-LM on-device edge engine (`litert-community/gemma-4-E2B-it-litert-lm`, 2.4 GB) with singleton caching (`generate_answer`).
  - `helpers.py`: Model health check utility (`check_model_available`, `get_model_status`).
- `src/ui/`:
  - `app.py`: Two-page Streamlit UI (📝 Add Memory · ❓ Ask Question). Startup model check, sample data loader, graceful error handling. Sidebar shows live memory count, model status, and demo tools. Retrieved memories display match badges (`⚡ Common`, `🧠 Semantic`, `🔤 BM25`), Semantic Cosine score, BM25 score, and Fused RRF score.
- `src/config.py`: Central Pydantic settings (`BaseSettings` backed by `.env` with `MEMORY_` prefix).
- `data/memories.db`: Local embedded SQLite database with FTS5 search index.

## Quick Start

### 1. Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- Google LiteRT-LM with Gemma 4 E2B on-device model (`task pull-model`)

### 2. Install Dependencies & Download Model
```bash
uv sync
task pull-model  # Downloads Gemma 4 E2B LiteRT-LM model (~2.4 GB)
```

### 3. Run the App
```bash
task run
# or directly:
uv run streamlit run src/ui/app.py
```

Opens at `http://localhost:8501`.  
- **📝 Add Memory** — paste any text; it's chunked, embedded, and stored.  
- **❓ Ask Question** — type a question; hybrid search retrieves relevant memories, Gemma 4 generates a grounded answer on-device.

### 4. Verify Everything Works (Pre-Demo Check)
```bash
# One-command health check — verifies DB, embedder, search, and model
task test-e2e

# Full pipeline test (requires memories in DB)
task test

# Verify configuration
task check-config
```

### 5. Inspect Database
The database is stored locally at `data/memories.db`. You can view and query it with:
- **VS Code Extension:** SQLite Viewer (by Florian Klampfer)
- **Dedicated GUI:** [DB Browser for SQLite](https://sqlitebrowser.org/) (recommended)
- **Universal GUI:** DBeaver (connect via SQLite driver pointing to `data/memories.db`)

## Troubleshooting

| Problem | Solution |
|---|---|
| **Model not found** error on startup | Run `task pull-model` to download Gemma 4 E2B (~2.4 GB). Requires internet. |
| **Embedding model download** hangs | First run downloads `BAAI/bge-small-en-v1.5` (~45 MB). Needs internet once; cached after. |
| **Port 8501 already in use** | Another Streamlit instance is running. Kill it or use `uv run streamlit run src/ui/app.py --server.port 8502`. |
| **Out of memory** during generation | Close other heavy apps. Gemma 4 E2B needs ~2-3 GB RAM. |
| **Slow first question** | The LLM engine loads on the first question (~10-30s). Subsequent questions are faster. |

## Demo Tips

1. **Quick setup:** Click the **🧪 Demo Tools** expander in the sidebar → **Load Sample Memories** to instantly populate 5 memories.
2. **Best demo questions:** "When is my dentist appointment?", "What is my brother's name?", "Do I prefer tea or coffee?"
3. **Show retrieval working:** After getting an answer, expand the **📚 Retrieved Memories** section to show the supervisor how semantic + BM25 hybrid search selects the right memories with scores.
4. **Show it's local:** Point out the sidebar shows "Local-first · On-device AI · No cloud" — no API keys, no internet needed after setup.
5. **Expected timings:** Adding a memory: ~1s. Searching: ~instant. LLM answer: 10-30s first time, ~5-15s after.

See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) for the full specification and roadmap.
