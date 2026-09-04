# Phase 1 Implementation Plan — Persistent Memory App

**Goal:** Prove the core loop works — user types memory → app stores it → user asks question → app retrieves relevant memory → app generates grounded answer using local LLM.

**Success criteria:**
- User can add several memories through the UI
- User can ask a natural-language question and get a correct, grounded answer
- Retrieval step is visible (show which memories were retrieved)
- Runs fully offline once models are pulled

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.10+ | Spec requirement |
| Package manager | `uv` | INSTRUCTIONS.md rule |
| UI | **Streamlit** | Fastest to prototype, looks like a product, not a terminal script |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) | Small, fast, local, proven |
| Storage | SQLite via `sqlite3` + JSON for embeddings | Simple, no vector DB needed at this scale |
| Similarity search | numpy brute-force cosine similarity | Spec says brute-force is preferred |
| LLM generation | Ollama + Gemma (2B or small variant) | Spec default choice |
| Config | Pydantic Settings | INSTRUCTIONS.md rule (no direct env vars) |

---

## Folder Structure (Feature-Based)

```
FYP_Demo/
├── main.py                  # Entry point (thin — launches Streamlit)
├── pyproject.toml
├── uv.lock
├── Taskfile.yml             # Task runner shortcuts
├── .env.example             # Example environment variables
├── INSTRUCTIONS.md
├── PROJECT_SPEC.md
├── README.md
├── docs/
│   ├── plans/
│   │   ├── 01-phase1-implementation.md  ← you are here
│   │   ├── 01-step01-project-setup.md
│   │   ├── 02-step02-storage-layer.md
│   │   ├── 03-step03-capture-layer.md
│   │   ├── 04-step04-embedding-wrapper.md
│   │   ├── 05-step05-retrieval-search.md
│   │   ├── 06-step06-generation-llm.md
│   │   ├── 07-step07-streamlit-ui.md
│   │   └── 08-step08-integration-test.md
│   └── additional/
├── src/
│   ├── __init__.py
│   ├── config.py            # Central Pydantic Settings
│   ├── memories/            # Feature: Memory capture, storage, embedding & search
│   │   ├── __init__.py
│   │   ├── models.py        # MemoryRecord schema
│   │   ├── database.py      # SQLite connection & table creation
│   │   ├── repository.py    # CRUD operations
│   │   ├── embedder.py      # Local Sentence-Transformers wrapper
│   │   └── service.py       # Capture normalization & similarity search
│   ├── assistant/           # Feature: Grounded Q&A / Ollama generation
│   │   ├── __init__.py
│   │   └── llm.py           # Prompt builder & Ollama client
│   └── ui/                  # Feature: Streamlit User Interface
│       ├── __init__.py
│       └── app.py           # Two-page web application
├── data/
│   └── memories.db          # Local SQLite storage (gitignored)
└── .gitignore
```

---

## Steps (click to open)

| # | Step | Status | Depends On |
|---|---|---|---|
| 01 | [Project Setup & Dependencies](✅%2001-step01-project-setup.md) | ✅ Approved | — |
| 02 | [Storage Layer](02-step02-storage-layer.md) | 🔲 Not started | 01 |
| 03 | [Capture Layer](03-step03-capture-layer.md) | 🔲 Not started | 01, 02, 04 |
| 04 | [Embedding Wrapper](04-step04-embedding-wrapper.md) | 🔲 Not started | 01 |
| 05 | [Retrieval / Similarity Search](05-step05-retrieval-search.md) | 🔲 Not started | 01, 02, 04 |
| 06 | [Generation / Ollama + Gemma](06-step06-generation-llm.md) | 🔲 Not started | 01 *(parallel with 02 & 04)* |
| 07 | [Streamlit UI](07-step07-streamlit-ui.md) | 🔲 Not started | 01–06 |
| 08 | [Integration Test & Polish](08-step08-integration-test.md) | 🔲 Not started | 01–07 |

---

## Dependency Graph

```
Step 01 (Setup)
  ├── Step 02 (Storage) ──────┐
  ├── Step 04 (Embedding) ────┼──▶ Step 03 (Capture)  ──┐
  │                           └──▶ Step 05 (Retrieval) ──┤
  └── Step 06 (Generation) ──────────────────────────────┤
                                                         ▼
                                               Step 07 (UI) ──▶ Step 08 (Test)
```

Steps 02, 04, and 06 are all fully parallel after Step 01 — none of them depend on each other. Steps 03 and 05 both need 02 + 04. Step 06 (Generation) is independent of Steps 02–05 and can be built at any time after Step 01.

---

## Working Cadence

1. Pick a step
2. Read its full doc
3. Make your decisions (the ⚖️ sections in each step)
4. Tell me to implement it
5. I build it, test it, hand it to you
6. You verify, approve, we move on

Start with Step 01 when ready.
