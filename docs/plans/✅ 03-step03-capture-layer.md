# Step 03 — Capture Layer (Text Input Normalization)

**Status:** 🔲 Not started  
**Depends on:** Steps 01, 02, 04  
**Blocks:** Step 07 (UI)

---

## What This Step Does

Takes raw text from the user, validates it, embeds it into a vector, and wraps it into a `MemoryRecord` ready for storage.

## Why This Matters

Separation of concerns: the capture layer doesn't know about SQLite or Ollama. It just normalizes input. This means when Phase 2 adds audio input, we only add a new capture adapter — nothing else changes.

---

## What Gets Created

| File | Purpose |
|---|---|
| `src/memories/service.py` | `create_memory_from_text()` function (feature-based structure) |

---

## How It Works

```
User types: "I have a dentist appointment on the 14th"
        │
        ▼
memories/service.py
        │
        ├─ Validate (reject empty or whitespace-only strings)
        ├─ Call embedder.embed(text) → [0.12, -0.03, ...] (384 floats, normalized)
        ├─ Attach timestamp (datetime.now())
        ├─ Set source_type = "text"
        │
        ▼
MemoryRecord(text=..., embedding=..., timestamp=..., source_type="text")
        │
        ▼
Ready for memories.repository.save_memory()
```

---

## ⚖️ Decisions You Need to Make

### 1. Text Validation Rules

How strict should input validation be?

| Rule | Strict | Lenient |
|---|---|---|
| Empty text | Reject | Reject |
| Min length | 3+ characters | Any non-empty |
| Max length | 10,000 chars | No limit |
| Whitespace only | Reject | Reject |

**My recommendation:** Lenient — reject empty/whitespace-only, but no min/max length. Let the user write what they want.

**You decide:** How strict?

---

### 2. Should We Auto-Chunk Long Text?

**Decision (Approved by User):** Split into token-bounded chunks.
- **Average Chunk Size:** 256 tokens.
- **Overlap:** 30 to 50 tokens (~10%–15%, default 40 tokens).
- **Strict Upper Ceiling:** 400 tokens (hard guarantee per chunk).
- **Database Metadata:** Persist `{"chunk_index": i, "total_chunks": N, "token_count": T}` for every row.

---

### 3. Duplicate Detection

**Recommendation:** No duplicate check for Phase 1 per Ponytail YAGNI (simulates realistic human notes and exercises semantic retrieval).

---

## How to Implement

Create `src/memories/service.py`:

```python
from datetime import datetime

from src.memories.embedder import Embedder
from src.memories.models import MemoryRecord

DEFAULT_CHUNK_SIZE = 256
DEFAULT_OVERLAP = 40  # 30-50 tokens (~15%)
STRICT_UPPER_CEILING = 400


def chunk_text_by_tokens(
    text: str,
    embedder: Embedder,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    strict_ceiling: int = STRICT_UPPER_CEILING,
) -> list[tuple[str, int]]:
    tokens = embedder.tokenize(text)
    total_tokens = len(tokens)
    if total_tokens <= chunk_size:
        return [(text, total_tokens)]

    chunks: list[tuple[str, int]] = []
    step = max(1, chunk_size - overlap)
    start = 0
    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        if end - start > strict_ceiling:
            end = start + strict_ceiling
        chunk_tokens = tokens[start:end]
        chunk_str = embedder.decode_tokens(chunk_tokens)
        chunks.append((chunk_str, len(chunk_tokens)))
        if end == total_tokens:
            break
        start += step
    return chunks


def create_memories_from_text(
    text: str,
    embedder: Embedder | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    strict_ceiling: int = STRICT_UPPER_CEILING,
) -> list[MemoryRecord]:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Memory text cannot be empty or whitespace only")

    if embedder is None:
        embedder = Embedder()

    chunks = chunk_text_by_tokens(
        cleaned,
        embedder=embedder,
        chunk_size=chunk_size,
        overlap=overlap,
        strict_ceiling=strict_ceiling,
    )

    chunk_texts = [c[0] for c in chunks]
    embeddings = embedder.embed_batch(chunk_texts)
    now = datetime.now()
    total_chunks = len(chunks)

    records: list[MemoryRecord] = []
    for idx, ((chunk_str, token_count), embedding) in enumerate(zip(chunks, embeddings)):
        records.append(
            MemoryRecord(
                text=chunk_str,
                embedding=embedding,
                timestamp=now,
                source_type="text",
                metadata={
                    "chunk_index": idx,
                    "total_chunks": total_chunks,
                    "token_count": token_count,
                },
            )
        )
    return records


def create_memory_from_text(
    text: str,
    embedder: Embedder | None = None,
) -> MemoryRecord:
    records = create_memories_from_text(text, embedder=embedder)
    return records[0]
```

---

## Verification

```bash
uv run python -c "
from src.memories import create_memories_from_text, Embedder

emb = Embedder()
long_text = 'Machine learning representations. ' * 45
records = create_memories_from_text(long_text, emb)
print(f'Total chunks: {len(records)}')
for r in records:
    print('Chunk:', r.metadata)
"
```

---

## Research Notes

- [x] Text validation: Reject empty and whitespace-only strings with `strip()`.
- [x] Token chunking: 256 avg chunk size, 30-50 tokens overlap, 400 tokens strict ceiling.
- [x] Chunk metadata: Added `metadata` JSON field on `MemoryRecord` and SQLite `memories` table.
- [x] Tokenizer reuse: Reuses underlying `SentenceTransformer.tokenizer` directly without external packages.

---

## Files Changed

- `src/memories/models.py` (added `metadata` field)
- `src/memories/database.py` (added `metadata` column + migration)
- `src/memories/repository.py` (added metadata persistence and `save_memories`)
- `src/memories/embedder.py` (added `count_tokens`, `tokenize`, `decode_tokens`)
- `src/memories/service.py` (`chunk_text_by_tokens`, `create_memories_from_text`, `create_memory_from_text`)
- `src/memories/__init__.py` (re-exports)
- `Taskfile.yml` (updated test task)


