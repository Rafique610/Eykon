# Step 05 — Retrieval Layer (Similarity Search)

**Status:** 🔲 Not started  
**Depends on:** Steps 01, 02, 04  
**Blocks:** Steps 06, 07

---

## What This Step Does

Given a user's question, finds the top-k most similar stored memories using cosine similarity over their embedding vectors.

## Why This Matters

This is the "R" in RAG. Without good retrieval, the LLM gets garbage context and gives garbage answers. This step determines whether the app actually works.

---

## What Gets Created

| File | Purpose |
|---|---|
| `src/memories/search.py` | `search_memories()` — hybrid (dense + sparse RRF), semantic, and keyword search |
| `src/memories/database.py` | FTS5 virtual table and synchronization triggers |

---

## How It Works

```
User asks: "When is my dentist appointment?"
        │
        ▼
search_memories(query, embedder, top_k=5, mode="hybrid")
        │
        ├─ 1. Dense Semantic Search:
        │      query_vector = embedder.embed(query)
        │      similarities = dot(mem_vectors, query_vector)
        │      Rank candidate memories by cosine similarity
        │
        ├─ 2. Sparse Keyword Search:
        │      Query SQLite FTS5 (BM25) on memories_fts
        │      Rank candidate memories by keyword relevance
        │
        ├─ 3. Reciprocal Rank Fusion (RRF):
        │      RRF_Score = 1/(60 + dense_rank) + 1/(60 + sparse_rank)
        │      Sort by combined RRF score descending
        │
        ▼
[
  (MemoryRecord(text="Dentist on the 14th"), 0.0328),
  (MemoryRecord(text="Doctor visit Friday"), 0.0161),
  ...
]
```

---

## ⚖️ Decisions Made

### 1. Retrieval Strategy: Hybrid Search (Approved by User)
- **Dense Vector Search:** Fast cosine similarity via `np.dot` over unit-normalized BGE embeddings.
- **Sparse Keyword Search:** Native SQLite `FTS5` virtual table (`memories_fts`) with automatic sync triggers (`memories_ai`, `memories_ad`, `memories_au`).
- **Fusion:** Reciprocal Rank Fusion (RRF with $k=60$) in pure Python (zero extra dependencies).

### 2. Default Top-K Value: 5 (Recommended)
- Returns top 5 memories by default, configurable via `Settings().TOP_K` or parameter.

### 3. Similarity Threshold: None for Phase 1 (Recommended)
- Returns top-K candidates directly; LLM prompt instructs whether context contains sufficient facts.

### 4. Search Strategy: Vectorized Dot Product + FTS5 BM25 (Recommended)
- High throughput, exact similarity, zero heavy dependencies (FAISS/Annoy not needed).

---

## How to Implement

Created `src/memories/search.py`:

```python
import re
from pathlib import Path
import numpy as np
from src.config import Settings
from src.memories.database import get_connection
from src.memories.embedder import Embedder
from src.memories.models import MemoryRecord
from src.memories.repository import get_all_memories, get_memory_by_id

RRF_K = 60

def search_memories(
    query: str,
    embedder: Embedder | None = None,
    top_k: int | None = None,
    mode: str = "hybrid",
    db_path: Path | str | None = None,
) -> list[tuple[MemoryRecord, float]]:
    ...
```

---

## Verification

```bash
uv run python -c "
from src.memories import init_db, clear_all_memories, save_memories, create_memories_from_text, search_memories, Embedder

init_db()
clear_all_memories()
emb = Embedder()

for note in [
    'I have an appointment with dentist Dr. Smith on Tuesday at 3pm.',
    'Ali phone number is +92-300-1234567.',
    'The secret project codename is Eykon.',
]:
    save_memories(create_memories_from_text(note, emb))

hits = search_memories('When do I see the dentist?', emb, top_k=2)
for r, score in hits:
    print(f'[{score:.4f}] {r.text}')
"
```

---

## Files Changed

- `src/memories/database.py` (added FTS5 virtual table + triggers + rebuild)
- `src/memories/search.py` (new hybrid search implementation)
- `src/memories/__init__.py` (re-export `search_memories`)
- `Taskfile.yml` (updated test command)

