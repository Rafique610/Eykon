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
| `src/capture/text.py` | `create_memory_from_text()` function |

---

## How It Works

```
User types: "I have a dentist appointment on the 14th"
        │
        ▼
capture/text.py
        │
        ├─ Validate (non-empty? reasonable length?)
        ├─ Call embedder.embed(text) → [0.12, -0.03, ...] (384 floats)
        ├─ Attach timestamp (now)
        ├─ Set source_type = "text"
        │
        ▼
MemoryRecord(text=..., embedding=..., timestamp=..., source_type="text")
        │
        ▼
Ready for storage.repository.save_memory()
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

If a user pastes a long paragraph (500+ words), should we:

| Approach | Pros | Cons |
|---|---|---|
| Store as-is | Simple, preserves original | Long text = weaker embedding |
| Split into chunks | Better embeddings per chunk | Need to handle overlap, reassembly |
| Warn user | Transparent | Annoying |

**My recommendation:** Store as-is for Phase 1. Long text embeddings are "good enough" for a demo. Chunking adds complexity.

**You decide:** Store as-is or chunk?

---

### 3. Duplicate Detection

Should we check if the user is submitting a memory that's nearly identical to one already stored?

| Approach | Pros | Cons |
|---|---|---|
| No check | Simple | User might store duplicates |
| Warn on high similarity | Prevents duplicates | Needs threshold tuning |
| Auto-merge | Smart | Complex, might merge wrong things |

**My recommendation:** No check for Phase 1. Duplicates are fine — they're actually useful for the demo (shows retrieval works even with similar content).

**You decide:** Add duplicate detection?

---

## How to Implement

Create `src/capture/text.py`:

```python
from datetime import datetime
from src.storage.models import MemoryRecord

def create_memory_from_text(text: str, embedder) -> MemoryRecord:
    """
    Takes raw text and an embedder instance.
    Returns a complete MemoryRecord ready for storage.
    """
    # Validate
    text = text.strip()
    if not text:
        raise ValueError("Memory text cannot be empty")
    
    # Embed
    embedding = embedder.embed(text)
    
    # Build record
    return MemoryRecord(
        text=text,
        embedding=embedding,
        timestamp=datetime.now(),
        source_type="text",
    )
```

---

## Verification

```bash
# Requires embedder from Step 04 to be implemented
uv run python -c "
from src.capture.text import create_memory_from_text
from src.retrieval.embedder import Embedder

emb = Embedder()
rec = create_memory_from_text('I have a dentist appointment on the 14th', emb)
print(f'Text: {rec.text}')
print(f'Embedding dim: {len(rec.embedding)}')
print(f'Source: {rec.source_type}')
print(f'Timestamp: {rec.timestamp}')
"
```

---

## Research Notes

> _Leave your notes here as you research._

- [ ] How strict should validation be?
- [ ] Should we chunk long text or store as-is?
- [ ] Add duplicate detection now or later?
- [ ] Any edge cases I'm not thinking of?

---

## Files Changed

- `src/capture/text.py` (new)
