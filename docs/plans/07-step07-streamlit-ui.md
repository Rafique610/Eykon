# Step 07 — Streamlit UI (Two Pages)

**Status:** 🔲 Not started  
**Depends on:** Steps 01–06  
**Blocks:** Step 08

---

## What This Step Does

Builds the user-facing interface with two pages: "Add Memory" and "Ask Question." This is what the supervisor sees during the demo.

## Why This Matters

The spec says "it should look and feel like a small product, not a terminal script." A good UI makes the demo convincing.

---

## What Gets Created

| File | Purpose |
|---|---|
| `src/ui/app.py` | Streamlit app with two pages |

---

## UI Layout

```
┌─────────────────────────────────────────────────┐
│  🧠 Persistent Memory App                       │
├──────────────┬──────────────────────────────────┤
│  📝 Add      │                                  │
│  ❓ Ask      │    [Main content area]            │
│              │                                  │
│  Status:     │                                  │
│  🟢 Ollama   │                                  │
│  📊 12 mems  │                                  │
└──────────────┴──────────────────────────────────┘
```

### Page 1 — Add Memory

```
┌─────────────────────────────────────────────────┐
│  Add a New Memory                               │
│                                                 │
│  ┌────────────────────────────────────────────┐ │
│  │ Type your memory here...                   │ │
│  │                                            │ │
│  │                                            │ │
│  └────────────────────────────────────────────┘ │
│                                                 │
│  [💾 Save Memory]                               │
│                                                 │
│  ✅ Memory saved! (ID: 15)                      │
│  📊 Total memories: 15                          │
└─────────────────────────────────────────────────┘
```

### Page 2 — Ask Question

```
┌─────────────────────────────────────────────────┐
│  Ask About Your Memories                        │
│                                                 │
│  ┌────────────────────────────────────────────┐ │
│  │ When is my dentist appointment?            │ │
│  └────────────────────────────────────────────┘ │
│                                                 │
│  [🔍 Ask]                                       │
│                                                 │
│  💡 Answer                                      │
│  Your dentist appointment is on the 14th.       │
│                                                 │
│  📚 Retrieved Memories (3 found)                │
│  ┌──────────────────────────────────────────┐   │
│  │ 1. Dentist appointment on the 14th (0.87)│   │
│  │ 2. Doctor visit Friday (0.62)            │   │
│  │ 3. Medical checkup next month (0.45)     │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## ⚖️ Decisions You Need to Make

### 1. Page Navigation: Sidebar vs Tabs vs Radio

| Approach | Pros | Cons |
|---|---|---|
| Sidebar (st.sidebar) | Clean, always visible | Takes horizontal space |
| Tabs (st.tabs) | Compact, familiar | Less prominent |
| Radio buttons | Simplest | Looks basic |

**My recommendation:** Sidebar. It's always visible, clean, and the demo supervisor can easily switch between pages.

**You decide:** Which navigation style?

---

### 2. What to Show After Saving a Memory

| Option | What user sees |
|---|---|
| Just confirmation | "Memory saved! (ID: 15)" |
| Confirmation + text echo | "Saved: 'Dentist on the 14th'" |
| Confirmation + full record | Show all fields including embedding preview |
| Auto-clear input | Clear the text area after save |

**My recommendation:** Confirmation + text echo. Shows the user exactly what was stored.

**You decide:** What to show after save?

---

### 3. Loading States

Embedding and LLM calls can take 1–10 seconds. How to show progress?

| Approach | Pros | Cons |
|---|---|---|
| st.spinner("Generating...") | Simple, built-in | Only shows one message |
| st.progress() bar | Visual feedback | Doesn't know total time |
| Multiple spinners | Granular (embedding → searching → generating) | More code |

**My recommendation:** `st.spinner()` with phases: "Embedding question...", "Searching memories...", "Generating answer..."

**You decide:** How detailed should loading states be?

---

### 4. Memory Count Display

Where to show how many memories are stored?

| Location | Visibility |
|---|---|
| Sidebar (always visible) | Always there |
| Add Memory page only | Only on that page |
| Both pages | Best of both |

**My recommendation:** Sidebar — always visible, so the user always knows the state.

**You decide:** Where to show memory count?

---

### 5. Show Retrieved Memories to User?

The spec says "retrieval step is visibly working." But how much to show?

| Level | What user sees |
|---|---|
| Minimal | Just the answer |
| Text + score | Memory text and similarity score |
| Full record | Text, score, timestamp, source type |

**My recommendation:** Text + score. Enough to prove retrieval works, not overwhelming.

**You decide:** How much detail on retrieved memories?

---

## How to Implement

Create `src/ui/app.py`:

```python
import streamlit as st
from src.config import Settings
from src.storage.database import init_db
from src.storage.repository import save_memory, count_memories
from src.capture.text import create_memory_from_text
from src.retrieval.embedder import Embedder
from src.retrieval.search import search_memories
from src.generation.llm import generate_answer

# Initialize
st.set_page_config(page_title="Memory App", page_icon="🧠")
init_db()

# Load embedder once (cached)
@st.cache_resource
def load_embedder():
    return Embedder()

embedder = load_embedder()

# Sidebar
with st.sidebar:
    st.title("🧠 Memory App")
    page = st.radio("Navigate", ["📝 Add Memory", "❓ Ask Question"])
    st.divider()
    count = count_memories()
    st.metric("Memories stored", count)

# Page 1: Add Memory
if page == "📝 Add Memory":
    st.header("Add a New Memory")
    text = st.text_area("Type your memory:", height=150)
    if st.button("💾 Save Memory"):
        if text.strip():
            record = create_memory_from_text(text, embedder)
            memory_id = save_memory(record)
            st.success(f"Memory saved! (ID: {memory_id})")
            st.rerun()  # Update count
        else:
            st.error("Please enter some text.")

# Page 2: Ask Question
elif page == "❓ Ask Question":
    st.header("Ask About Your Memories")
    question = st.text_input("Your question:")
    if st.button("🔍 Ask"):
        if question.strip():
            with st.spinner("Searching memories..."):
                results = search_memories(question, embedder)
            with st.spinner("Generating answer..."):
                answer = generate_answer(question, [r[0] for r in results])
            
            st.subheader("💡 Answer")
            st.write(answer)
            
            st.subheader(f"📚 Retrieved Memories ({len(results)} found)")
            for i, (rec, score) in enumerate(results, 1):
                st.write(f"{i}. {rec.text} *({score:.2f})*")
        else:
            st.error("Please enter a question.")
```

---

## Verification

```bash
uv run streamlit run src/ui/app.py
```

Manual test:
1. Add 3-5 memories
2. Ask "When is my dentist appointment?" → should reference the appointment
3. Ask "What does my brother like?" → should say "I don't have that information"
4. Verify retrieved memories are shown with scores
5. Verify memory count updates in sidebar

---

## Research Notes

> _Leave your notes here as you research._

- [ ] Sidebar vs tabs vs radio for navigation?
- [ ] What to show after saving a memory?
- [ ] How detailed should loading states be?
- [ ] Where to show memory count?
- [ ] How much detail on retrieved memories?
- [ ] Any Streamlit gotchas on Windows?

---

## How to Run

```bash
# Primary method (via Taskfile):
task run

# Alternative (direct):
uv run streamlit run src/ui/app.py

# Alternative (via main.py subprocess wrapper — set up in Step 01):
uv run python main.py
```

Streamlit opens at `http://localhost:8501`.

---

## Files Changed

- `src/ui/app.py` (new)
- `main.py` (already updated in Step 01 — this step just verifies it launches correctly)
