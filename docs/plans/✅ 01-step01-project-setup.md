# Step 01 — Project Setup & Dependencies

**Status:** ✅ Approved  
**Depends on:** Nothing  
**Blocks:** Everything

---

## What This Step Does

Sets up the skeleton of the project — folder structure, all Python dependencies, and a central config file. After this step, the project is ready for actual code.

## Why This Matters

A clean foundation prevents headaches later. If folders are wrong or dependencies are missing, every subsequent step inherits that mess.

---

## What Gets Created

```
FYP_Demo/
├── src/
│   ├── __init__.py
│   ├── config.py            ← Pydantic Settings (central config)
│   ├── memories/            ← Feature: capture, storage, embedding, search
│   │   └── __init__.py
│   ├── assistant/           ← Feature: prompt building, Ollama generation
│   │   └── __init__.py
│   └── ui/                  ← Feature: Streamlit UI
│       └── __init__.py
├── data/                    ← SQLite DB lives here (git-ignored)
├── Taskfile.yml             ← Project task runner
├── .env.example             ← Environment variable template
├── README.md                ← Project README stub
└── .gitignore (updated)
```

---

## Dependencies Being Added

| Package | Purpose | Size/Notes |
|---|---|---|
| `streamlit` | Web UI framework | ~100MB, fast to build with |
| `sentence-transformers` | Text → embedding vectors | ~500MB (includes PyTorch), downloads model on first use |
| `numpy` | Cosine similarity math | Tiny, fast |
| `ollama` | Python client for Ollama API | Tiny, just HTTP calls |
| `pydantic-settings` | Config management from env vars | Tiny |

---

## ⚖️ Decisions You Need to Make

### 1. UI Framework: Streamlit vs Gradio

The spec says "Streamlit or Gradio." Here's the tradeoff:

| | Streamlit | Gradio |
|---|---|---|
| Multi-page apps | Built-in sidebar nav | Need `gr.Tabs` or separate Blocks |
| Layout control | More flexible | Simpler but less control |
| Demo look | Looks more like a real product | Looks more like a demo |
| Learning curve | Slightly more | Slightly less |
| Speed to build | Fast | Faster for simple stuff |

**My recommendation:** Streamlit — better for a multi-page app where you want it to feel like a product.

**You decide:** Which one? Or do you want to try one and switch later?

---

### 2. Embedding Model: all-MiniLM-L6-v2 vs alternatives

The plan uses `all-MiniLM-L6-v2`. Here's why and what else exists:

| Model | Dimension | Speed | Quality | Download Size |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | Fast | Good for general text | ~90MB |
| `all-mpnet-base-v2` | 768 | Slower | Better quality | ~420MB |
| `bge-small-en-v1.5` | 384 | Fast | Very good | ~130MB |

**My recommendation:** `all-MiniLM-L6-v2` — fastest, smallest, good enough for personal memory retrieval.

**You decide:** Stick with MiniLM, or want to research alternatives?

---

### 3. Ollama Model: Gemma 2B vs other options

The spec says "Gemma (a small variant)." Here's what's available:

| Model | RAM Needed | Speed | Quality |
|---|---|---|---|
| `gemma2:2b` | ~3GB | Fast | Decent for simple QA |
| `gemma2:9b` | ~8GB | Slower | Much better |
| `phi3:mini` (3.8B) | ~4GB | Fast | Good, different style |
| `llama3.2:3b` | ~4GB | Fast | Good |

**My recommendation:** `gemma2:2b` — matches spec, runs on most machines.

**You decide:** What model do you have the RAM for? Do you want to test multiple?

---

## How to Implement

1. Create all folders + `__init__.py` files

2. Update `pyproject.toml` with the dependency list and run `uv sync`

3. Create `src/config.py` with Pydantic `Settings`:
   ```python
   from pydantic_settings import BaseSettings, SettingsConfigDict

   class Settings(BaseSettings):
       model_config = SettingsConfigDict(env_prefix="MEMORY_", env_file=".env")
       
       OLLAMA_BASE_URL: str = "http://localhost:11434"
       OLLAMA_MODEL: str = "gemma2:2b"
       EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
       DB_PATH: str = "data/memories.db"
       TOP_K: int = 5
   ```

4. Create `.env.example` (documents all available env vars — users copy this to `.env` to override):
   ```ini
   # Copy this file to .env and edit as needed
   # All values shown are the defaults — you only need to set what you want to change

   # MEMORY_OLLAMA_BASE_URL=http://localhost:11434
   # MEMORY_OLLAMA_MODEL=gemma2:2b
   # MEMORY_EMBEDDING_MODEL=all-MiniLM-L6-v2
   # MEMORY_DB_PATH=data/memories.db
   # MEMORY_TOP_K=5
   ```

5. Create `Taskfile.yml` (per INSTRUCTIONS.md §6 — users should never need to memorize raw commands):
   ```yaml
   version: '3'
   tasks:
     run:
       desc: Start the Streamlit app
       cmd: uv run streamlit run src/ui/app.py

     pull-model:
       desc: Pull the default Ollama model (gemma2:2b)
       cmd: ollama pull gemma2:2b

     install:
       desc: Install all Python dependencies
       cmd: uv sync

     check-config:
       desc: Print resolved config (useful for debugging)
       cmd: uv run python -c "from src.config import Settings; print(Settings())"
   ```

6. Update `main.py` — it should be a thin launcher that runs Streamlit as a subprocess. This lets `uv run python main.py` work as an alternative to `uv run streamlit run src/ui/app.py`:
   ```python
   import subprocess, sys

   def main():
       subprocess.run(
           ["streamlit", "run", "src/ui/app.py"],
           check=True,
       )

   if __name__ == "__main__":
       main()
   ```
   > **Note:** The primary launch method is `task run` (or `uv run streamlit run src/ui/app.py` directly). `main.py` is a convenience wrapper only.

7. Update `.gitignore` (already done — includes `data/`, `.memory/`, `.env`, `.env.local`, `.gemini/`)

8. Create a README stub (full content comes in Step 08, but the file should not be empty):
   ```markdown
   # Persistent Memory App

   Local-first personal memory app. Store memories, ask questions, get grounded answers from a local LLM.

   > 🚧 Under construction — see `PROJECT_SPEC.md` for the full specification and `docs/plans/` for the implementation plan.

   ## Quick Start (after setup)

   ```bash
   task run
   ```
   ```

---

## Verification

```bash
# Install deps
uv sync

# Check config loads correctly
uv run python -c "from src.config import Settings; print(Settings())"

# Check Taskfile works
task --list
```

Should print all config values without errors. `task --list` should show: run, pull-model, install, check-config.

---

## Research Notes

> _Leave your notes here as you research._

- [ ] Which UI framework? _(Streamlit / Gradio / other)_
- [ ] Which embedding model? _(MiniLM / mpnet / bge / other)_
- [ ] Which Ollama model? _(gemma2:2b / gemma2:9b / phi3 / llama3.2 / other)_
- [ ] Any other dependencies I'm missing?

---

## Files Changed

- `pyproject.toml` (dependencies added)
- `main.py` (thin Streamlit launcher)
- `.gitignore` (already updated)
- `.env.example` (new — documents available env vars)
- `Taskfile.yml` (new — task runner per INSTRUCTIONS.md §6)
- `README.md` (stub added)
- `src/config.py` (new)
- All `src/**/__init__.py` files (new)
- `data/` folder (created, gitignored)

