# Backend Invariants (Python)

Rules for all Python backend code in this project.

## Runtime

- Python managed via `uv`. Never call `python` directly — use `uv run`.
- Project config in `pyproject.toml` + `uv.lock`.

## Architecture

- Feature-based folders: `src/memories/`, `src/assistant/`, `src/vision/`, etc.
- Each feature has: `models.py` (dataclasses), `repository.py` (DB access), `service.py` (business logic), `__init__.py` (public API re-exports).
- Singletons via module-level `_CACHE` variables with lazy init (see `embedder.py`, `reranker.py`, `llm.py`).

## Database Access

- Raw `sqlite3` with parameterized queries (`?` placeholders). This is the established project convention.
- All DB functions are module-level (not class-based) in `repository.py`.
- `init_db()` is idempotent — safe to call multiple times.
- FTS5 virtual table with triggers for full-text search sync.

## Settings / Config

- Single `Settings` class in `src/config.py` using `pydantic-settings`.
- Env prefix: `MEMORY_`.
- All config values accessed via `Settings()` — never `os.getenv()`.

## Embeddings

- Model: `BAAI/bge-small-en-v1.5` via `sentence-transformers`, 384 dimensions, normalized.
- `Embedder` class is a singleton cached via `@st.cache_resource` in UI, direct instantiation elsewhere.
- Batch embedding via `embed_batch()` for performance.

## LLM

- Gemma 4 E2B via LiteRT-LM Python API. Model file in `models/`.
- Engine cached as singleton via `get_engine()`.
- Confirmed multimodal — supports image + text inputs.

## Chunking

- Token-based: 256 avg / 40 overlap / 400 ceiling.
- Uses the embedder's tokenizer for token counting.

## Search

- Three modes: hybrid (default), semantic, keyword.
- Hybrid: Dense cosine + FTS5 BM25, fused via RRF (k=60).
- Optional cross-encoder reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
- Query expansion via static concept map (zero latency).

## Testing

- Benchmark suite in `src/benchmarks/` with separate `data/benchmark.db`.
- Metrics: Hit@K, MRR, NDCG, P@K, latency.
- Always provide terminal verification commands with every step handoff.
