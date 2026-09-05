# Step 08 — Integration Test & Polish

**Status:** ✅ Implemented  
**Depends on:** Steps 01–07  
**Blocks:** Nothing (final step)

---

## What This Step Does

End-to-end testing, error handling for edge cases, loading states, and README update. Makes sure the demo actually works when the supervisor tries it.

## Why This Matters

A demo that crashes is worse than no demo. This step catches the issues that individual step testing misses.

---

## What Gets Done

| Area | Work |
|---|---|
| Error handling | Ollama not running, empty inputs, model not found |
| Loading states | Spinners for embedding, search, and LLM generation |
| Edge cases | Empty database, very long text, special characters |
| README | Prerequisites, how to run, how to use |

---

## ⚖️ Decisions You Need to Make

### 1. How to Handle Ollama Not Running

| Approach | UX |
|---|---|
| Crash with error | Bad — user sees red error |
| Check on startup, show warning | Better — user knows before trying |
| Check per request, show inline error | Best — graceful degradation |

**My recommendation:** Check on startup + show warning in sidebar. Also handle gracefully per request.

**You decide:** How to handle Ollama status?

---

### 2. Should We Add a "Test with Sample Data" Button?

A button that pre-loads 5-10 sample memories so the demo can be shown instantly.

| Pros | Cons |
|---|---|
| Faster demo setup | Might confuse the user |
| Shows the app works immediately | Extra code to maintain |

**My recommendation:** Yes, add it. For a demo, speed matters. Hide it behind an "advanced" expander.

**You decide:** Add sample data button?

---

### 3. README Content

What should the README cover?

| Section | Content |
|---|---|
| What | One-sentence description |
| Why | FYP context |
| Prerequisites | Ollama, Python 3.10+, uv |
| Install | `uv sync` + `ollama pull gemma2:2b` |
| Run | `uv run streamlit run src/ui/app.py` |
| Usage | How to add memories, how to ask questions |
| Architecture | Brief overview with link to docs |

**My recommendation:** All of the above. Keep it concise.

**You decide:** Any extra README sections?

---

## How to Implement

### Error Handling

Update `src/ui/app.py` to handle:
- Ollama connection failure → show error in UI
- Empty memory submission → validation message
- Empty question → validation message
- Model not found → clear instructions

### Loading States

Add `st.spinner()` around:
- Embedding model loading (cached, but show on first load)
- Memory embedding (fast, but show for UX)
- Similarity search (fast, but show for UX)
- LLM generation (slow, definitely show)

### README Update

Update `README.md` with:
```markdown
# Persistent Memory App

A local-first personal memory app. Store memories, ask questions, get grounded answers.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) installed and running
- Gemma model pulled: `ollama pull gemma2:2b`

## Quick Start

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Start Ollama (if not already running):
   ```bash
   ollama serve
   ```

3. Run the app:
   ```bash
   uv run streamlit run src/ui/app.py
   ```

4. Open http://localhost:8501 in your browser.

## Usage

### Adding Memories
1. Click "Add Memory" in the sidebar
2. Type your memory (e.g., "I have a dentist appointment on the 14th")
3. Click "Save Memory"

### Asking Questions
1. Click "Ask Question" in the sidebar
2. Type your question (e.g., "When is my dentist appointment?")
3. Click "Ask"
4. See the answer and which memories were retrieved

## Architecture

See `PROJECT_SPEC.md` for the full project specification and architecture details.
```

---

## Verification

```bash
# Full manual test
uv run streamlit run src/ui/app.py
```

Test checklist:
- [ ] App starts without errors
- [ ] Ollama status shows in sidebar
- [ ] Can add a memory
- [ ] Memory count updates
- [ ] Can ask a question
- [ ] Answer is grounded in stored memories
- [ ] Retrieved memories are shown with scores
- [ ] Empty input shows validation error
- [ ] Ollama not running shows clear error message
- [ ] App doesn't crash on any edge case

---

## Research Notes

> _Leave your notes here as you research._

- [ ] How to check Ollama status from Python?
- [ ] Streamlit best practices for error handling?
- [ ] Any demo tips for making it look polished?

---

## Files Changed

- `src/ui/app.py` (error handling additions)
- `README.md` (updated)
- Various `src/` files (minor fixes)
