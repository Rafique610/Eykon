# Step 04 — Embedding Model Wrapper

**Status:** 🔲 Not started  
**Depends on:** Step 01  
**Blocks:** Steps 03, 05

---

## What This Step Does

Wraps `sentence-transformers` into a simple class that embeds text into 384-dimensional vectors. One model load, reused for all embeddings.

## Why This Matters

Embeddings are used by both capture (to store memories) and retrieval (to search memories). A single wrapper means consistent embeddings everywhere.

---

## What Gets Created

| File | Purpose |
|---|---|
| `src/retrieval/embedder.py` | `Embedder` class with `embed()` and `embed_batch()` |

---

## How It Works

```
Embedder.__init__()
    │
    ├─ Loads model: all-MiniLM-L6-v2 (one-time, ~90MB download)
    ├─ Model stays in memory for all subsequent calls
    │
    embed("I have a dentist appointment")
    │
    ├─ Tokenize text
    ├─ Run through transformer layers
    ├─ Pool → 384-dim vector
    │
    ▼
[0.12, -0.03, 0.45, ...] (384 floats)
```

---

## ⚖️ Decisions You Need to Make

### 1. Model Loading: Eager vs Lazy

| Approach | Pros | Cons |
|---|---|---|
| Eager (load in `__init__`) | First call is fast | Startup is slower |
| Lazy (load on first `embed()`) | Startup is instant | First embed call is slow |

**My recommendation:** Eager — load in `__init__`. The UI can show a "Loading model..." spinner during startup.

**You decide:** Eager or lazy?

---

### 2. Embedding Normalization

**⚠️ Critical: `encode()` does NOT normalize by default.** The `normalize_embeddings` parameter defaults to `False`. If you skip normalization, the dot product in step 05 produces wrong similarity rankings — the demo will give weird answers with no obvious error.

| Approach | Pros | Cons |
|---|---|---|
| Normalize at embed time (`normalize_embeddings=True`) | Clean — vectors are always unit length, dot = cosine | Slight overhead per embed call |
| Normalize at search time (in `search.py`) | Embedder stays pure | Easy to forget, risk of bug |

**My recommendation:** Normalize at embed time. One place, always correct. The `Embedder` owns the contract: "every vector it produces is a unit vector."

**You decide:** Normalize at embed time or search time?

---

### 3. Error Handling for Model Download

First run downloads the model. What if there's no internet?

| Approach | Behavior |
|---|---|
| Crash with error | Simple, user knows to fix it |
| Fallback to smaller model | Complex |
| Cache check + clear error message | Best UX |

**My recommendation:** Try to load, catch the error, raise a clear message: "Could not load embedding model. Check your internet connection for first run."

**You decide:** How to handle download failures?

---

## How to Implement

Create `src/retrieval/embedder.py`:

```python
from sentence_transformers import SentenceTransformer
from src.config import Settings

class Embedder:
    def __init__(self, model_name: str = None):
        settings = Settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = SentenceTransformer(self.model_name)
    
    def embed(self, text: str) -> list[float]:
        """Embed a single text into a 384-dim unit vector."""
        # normalize_embeddings=True ensures ||v|| ≈ 1.0, so dot product = cosine similarity
        return self._model.encode(text, normalize_embeddings=True).tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts at once (faster than one-by-one)."""
        return self._model.encode(texts, normalize_embeddings=True).tolist()
```

---

## Verification

```bash
uv run python -c "
from src.retrieval.embedder import Embedder

emb = Embedder()
v = emb.embed('Hello world')
print(f'Dimension: {len(v)}')
print(f'First 5 values: {v[:5]}')
print(f'Is normalized (norm≈1): {sum(x**2 for x in v)**0.5:.3f}')
"
```

Expected: dimension 384, norm ≈ 1.0

---

## Research Notes

> _Leave your notes here as you research._

- [ ] Eager vs lazy model loading?
- [ ] ✅ FIXED: Always normalize at embed time (`normalize_embeddings=True`)
- [ ] How to handle first-run model download?
- [ ] Any sentence-transformers gotchas on Windows?

---

## Files Changed

- `src/retrieval/embedder.py` (new)
