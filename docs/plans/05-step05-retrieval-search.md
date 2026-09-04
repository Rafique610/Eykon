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
| `src/retrieval/search.py` | `search_memories()` — the core search function |

---

## How It Works

```
User asks: "When is my dentist appointment?"
        │
        ▼
search_memories(query, embedder, top_k=5)
        │
        ├─ 1. Embed the query → [0.15, -0.02, ...]
        ├─ 2. Load ALL stored memories from SQLite
        ├─ 3. For each memory:
        │      similarity = dot(query_embedding, memory_embedding)
        ├─ 4. Sort by similarity (descending)
        ├─ 5. Return top-k
        │
        ▼
[
  (MemoryRecord(text="Dentist on the 14th"), 0.87),
  (MemoryRecord(text="Doctor visit Friday"), 0.62),
  ...
]
```

---

## ⚖️ Decisions You Need to Make

### 1. Default Top-K Value

How many memories should retrieval return?

| K | Pros | Cons |
|---|---|---|
| 3 | Fast, focused | Might miss relevant context |
| 5 | Good balance | Default in plan |
| 10 | More context for LLM | Might include irrelevant noise |

**My recommendation:** 5. You can always adjust via config. The LLM prompt should instruct it to only use relevant memories.

**You decide:** What default K?

---

### 2. Similarity Threshold

Should we filter out low-similarity results?

| Approach | Pros | Cons |
|---|---|---|
| No threshold | Always returns K results | Might return irrelevant stuff |
| Threshold (e.g. > 0.3) | Only returns relevant | Might return fewer than K results |
| Configurable threshold | Flexible | More config to manage |

**My recommendation:** No threshold for Phase 1. If all memories are irrelevant, the LLM prompt handles that ("If the answer is not in the memories, say so").

**You decide:** Add a similarity threshold?

---

### 3. Search Strategy: Brute-Force vs ANN

| Strategy | Pros | Cons |
|---|---|---|
| Brute-force (numpy dot) | Simple, exact, fast enough | Slows down at 10K+ records |
| FAISS | Fast at scale | Extra dependency, complex |
| Annoy | Fast, memory-efficient | Extra dependency |

**My recommendation:** Brute-force. The spec explicitly says this is fine. Hundreds of records = instant search. **This works because Step 04 normalizes embeddings to unit vectors**, so `np.dot(a, b)` equals cosine similarity. If normalization is skipped, this produces wrong rankings.

**You decide:** Stick with brute-force?

---

### 4. How to Display Results

When retrieval returns results, how should they be presented to the LLM and user?

| Approach | LLM sees | User sees |
|---|---|---|
| Text + score | Memory text + similarity score | Both |
| Text only | Just memory text | Text + score |
| Ranked list | Numbered list | Numbered list with scores |

**My recommendation:** LLM sees text only (scores confuse LLMs). User sees text + scores in the UI.

**You decide:** How to format results?

---

## How to Implement

Create `src/retrieval/search.py`:

```python
import numpy as np
from src.storage.repository import get_all_memories
from src.storage.models import MemoryRecord
from src.retrieval.embedder import Embedder
from src.config import Settings

def search_memories(
    query: str,
    embedder: Embedder,
    top_k: int = None,
) -> list[tuple[MemoryRecord, float]]:
    """
    Find the top-k most similar memories to the query.
    Returns list of (MemoryRecord, similarity_score) tuples.
    """
    settings = Settings()
    if top_k is None:
        top_k = settings.TOP_K
    
    # Embed the query
    query_embedding = np.array(embedder.embed(query))
    
    # Load all stored memories
    all_memories = get_all_memories()
    
    if not all_memories:
        return []
    
    # Compute similarities
    # NOTE: This is cosine similarity because Step 04 normalizes embeddings to unit vectors.
    # If embeddings are NOT normalized, replace with:
    #   norm_q = np.linalg.norm(query_embedding)
    #   norm_m = np.linalg.norm(mem_embedding)
    #   similarity = float(np.dot(query_embedding, mem_embedding) / (norm_q * norm_m))
    scores = []
    for memory in all_memories:
        mem_embedding = np.array(memory.embedding)
        similarity = float(np.dot(query_embedding, mem_embedding))
        scores.append((memory, similarity))
    
    # Sort by similarity (descending) and return top-k
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]
```

---

## Verification

```bash
uv run python -c "
from src.storage.database import init_db
from src.storage.repository import save_memory
from src.storage.models import MemoryRecord
from src.retrieval.embedder import Embedder
from src.retrieval.search import search_memories
from datetime import datetime

init_db()
emb = Embedder()

# Store some test memories
memories = [
    'I have a dentist appointment on the 14th',
    'My brother name is Ali',
    'I prefer tea over coffee',
    'My birthday is in March',
]
for m in memories:
    rec = MemoryRecord(text=m, embedding=emb.embed(m), timestamp=datetime.now(), source_type='text')
    save_memory(rec)

# Test retrieval
results = search_memories('When is my dentist appointment?', emb, top_k=2)
for rec, score in results:
    print(f'Score: {score:.3f} | {rec.text}')
"
```

Expected: "dentist appointment" should score highest for that query.

---

## Research Notes

> _Leave your notes here as you research._

- [ ] What default top-k?
- [ ] Add similarity threshold or not?
- [ ] Brute-force or ANN?
- [ ] How to format results for LLM vs user?
- [ ] Any numpy gotchas on Windows?

---

## Files Changed

- `src/retrieval/search.py` (new)
