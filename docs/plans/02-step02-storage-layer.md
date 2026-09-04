# Step 02 — Storage Layer (Models + SQLite + Repository)

**Status:** 🔲 Not started  
**Depends on:** Step 01  
**Blocks:** Steps 03, 05

---

## What This Step Does

Creates the data model for a "memory record," sets up a SQLite database to store them, and builds functions to save/retrieve/delete memories.

## Why This Matters

Everything flows through storage. The capture layer writes to it, the retrieval layer reads from it. If this is wrong, nothing works.

---

## What Gets Created

| File | Purpose |
|---|---|
| `src/storage/models.py` | `MemoryRecord` dataclass — the shape of every memory |
| `src/storage/database.py` | SQLite connection, table creation |
| `src/storage/repository.py` | CRUD functions (save, get all, get by ID, delete, count) |

---

## The Data Model

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(kw_only=True)
class MemoryRecord:
    text: str
    embedding: list[float]
    timestamp: datetime
    source_type: str = "text"
    id: int | None = None  # Auto-assigned by SQLite, not set on creation
```

**⚠️ `kw_only=True` is required.** `id` is auto-assigned by SQLite so it defaults to `None`. Python dataclasses require that once one field has a default, every field after it must also have one. Without `kw_only=True`, constructing `MemoryRecord(text=..., embedding=..., timestamp=...)` throws `TypeError` because `id` (with default) comes before required fields. `kw_only=True` lets all fields be passed as keyword arguments, bypassing the ordering constraint.

### How Embeddings Are Stored

Embeddings are vectors of 384 floats. SQLite doesn't have a native array type, so we store them as a JSON-serialized string:

```python
# Writing: json.dumps(embedding) → '[0.1, 0.2, ...]'
# Reading: json.loads(blob) → [0.1, 0.2, ...]
```

**Why not binary/pickle?** JSON is debuggable — you can open the DB and read it. At this scale, the performance difference is negligible.

---

## ⚖️ Decisions You Need to Make

### 1. SQLite vs JSON File

| | SQLite | JSON/Pickle File |
|---|---|---|
| Concurrent access | Safe | Not safe |
| Query flexibility | SQL queries | Load entire file |
| Scale | Thousands+ | Hundreds |
| Complexity | Slightly more | Simpler |
| Debugging | Easy (DB browser) | Easy (text file) |

**My recommendation:** SQLite — more robust, and not much harder to set up. If you want the absolute simplest start, JSON works fine for hundreds of records.

**You decide:** Which one?

---

### 2. Should We Add Metadata Fields Now?

The current model has: `id, text, embedding, timestamp, source_type`

Potential future fields to consider adding now (even if empty):

| Field | Why |
|---|---|
| `tags` | Categorize memories (e.g. "family", "work", "health") |
| `importance` | Rank memories by importance for retrieval weighting |
| `last_accessed` | Track when a memory was last used (for forgetting curves) |
| `source_id` | Link to original source (for audio/video in later phases) |

**My recommendation:** Keep it minimal for Phase 1. Add fields later when you need them. The spec says "start simple."

**You decide:** Add any extra fields now, or keep it minimal?

---

### 3. Repository Pattern: Functions vs Class

Two ways to organize the CRUD operations:

**Option A — Module-level functions (recommended):**
```python
# repository.py
def save_memory(record: MemoryRecord) -> int: ...
def get_all_memories() -> list[MemoryRecord]: ...
```

**Option B — Repository class:**
```python
# repository.py
class MemoryRepository:
    def __init__(self, db_path: str): ...
    def save(self, record: MemoryRecord) -> int: ...
```

**My recommendation:** Functions. Simpler, and at this scale there's no need for a class that holds state.

**You decide:** Functions or class?

---

## How to Implement

1. Create `src/storage/models.py`:
   - `MemoryRecord` dataclass with `@dataclass(kw_only=True)`
   - `id: int | None = None` (last field, auto-assigned by SQLite)
   - `to_dict()` and `from_dict()` methods for serialization

2. Create `src/storage/database.py`:
   - `init_db()` — creates the `memories` table if it doesn't exist
   - `get_connection()` — returns a SQLite connection
   - Table schema:
     ```sql
     CREATE TABLE IF NOT EXISTS memories (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         text TEXT NOT NULL,
         embedding TEXT NOT NULL,
         timestamp TEXT NOT NULL,
         source_type TEXT NOT NULL DEFAULT 'text'
     );
     ```

3. Create `src/storage/repository.py`:
   - `save_memory(record) -> int`
   - `get_all_memories() -> list[MemoryRecord]`
   - `get_memory_by_id(id) -> MemoryRecord | None`
   - `delete_memory(id) -> bool`
   - `count_memories() -> int`

---

## Verification

```bash
uv run python -c "
from src.storage.database import init_db
from src.storage.repository import save_memory, get_all_memories, count_memories
from src.storage.models import MemoryRecord
from datetime import datetime

init_db()
rec = MemoryRecord(text='Test memory', embedding=[0.1]*384, timestamp=datetime.now(), source_type='text')
mid = save_memory(rec)
print(f'Saved ID: {mid}, Count: {count_memories()}')
all_mem = get_all_memories()
print(f'Fetched: {all_mem[0].text}')
"
```

---

## Research Notes

> _Leave your notes here as you research._

- [ ] SQLite vs JSON file?
- [ ] Any extra metadata fields to add?
- [ ] Functions vs class-based repository?
- [ ] Any Python SQLite gotchas to watch for?

---

## ⚠️ Database Safety & Recovery

- `init_db()` is **idempotent** — it uses `CREATE TABLE IF NOT EXISTS`, so calling it on an existing DB is always safe.
- If `data/memories.db` is **deleted**, calling `init_db()` recreates the table from scratch (empty). All memories are lost — expected behaviour.
- If `data/memories.db` is **corrupted**, SQLite will raise an exception. The app should surface a clear error: "Database appears corrupted. Delete `data/memories.db` and restart to start fresh."
- **No backup mechanism for Phase 1** — this is intentional (prototype scope). For the demo, simply don't delete the DB. A future phase can add export/import.

---

## Files Changed

- `src/storage/models.py` (new)
- `src/storage/database.py` (new)
- `src/storage/repository.py` (new)
