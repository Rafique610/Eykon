# Step 06 — Generation Layer (Gemma 4 E2B via LiteRT-LM)

**Status:** 🔲 In Progress  
**Depends on:** Step 01, Step 05  
**Blocks:** Steps 07, 08

---

## What This Step Does

Takes the user's question + retrieved memories from Step 05, formats them into a strictly grounded RAG prompt, and passes them to **Google's on-device Gemma 4 E2B LiteRT-LM** engine to generate a natural, factual answer.

## Why This Matters

This is the "G" in RAG. Using **LiteRT-LM** directly aligns with the production mobile deployment target (Android / iOS / Edge), allowing us to benchmark latency, on-device memory footprint, and generation quality on the exact edge model (`gemma-4-E2B-it.litertlm`).

---

## What Gets Created

| File | Purpose |
|---|---|
| `src/assistant/prompt.py` | `build_rag_prompt()` — formats retrieved memories into strict RAG prompt |
| `src/assistant/llm.py` | `generate_answer()` — engine lifecycle and LiteRT-LM generation |
| `src/assistant/__init__.py` | Public exports for assistant feature |

---

## How It Works

```
User Question: "When is my dentist appointment?"
Retrieved Memories: [MemoryRecord(text="Dentist Dr. Smith on Tuesday at 3pm"), ...]
        │
        ▼
build_rag_prompt(question, context_memories)
        │
        ├─ Strict system instructions: "Answer ONLY based on stored memories..."
        ├─ Formatted context list: "[1] Dentist Dr. Smith on Tuesday at 3pm"
        ├─ User question
        │
        ▼
generate_answer(question, context_memories)
        │
        ├─ LiteRT-LM Engine (gemma-4-E2B-it.litertlm)
        ├─ Sampler: temperature=0.1, max_tokens=256
        │
        ▼
"Your dentist appointment with Dr. Smith is on Tuesday at 3pm."
```

---

## ⚖️ Decisions You Need to Make

### 1. Prompt Template

The prompt controls answer quality. Here are options:

| Style | Prompt | Effect |
|---|---|---|
| Strict | "Answer ONLY from memories. If not found, say 'I don't know.'" | Prevents hallucination |
| Helpful | "Answer from memories if available. If not, say what you think but clarify it's not from memories." | More flexible |
| Hybrid | "Answer from memories. You may add general knowledge but clearly label it." | Best of both |

**My recommendation:** Strict for Phase 1. Prevents hallucination, which is the #1 demo risk.

**You decide:** Which prompt style?

---

### 2. Ollama Call: Sync vs Async

| Approach | Pros | Cons |
|---|---|---|
| Synchronous | Simple | UI freezes during generation |
| Async (asyncio) | UI stays responsive | More complex code |
| Threading | UI stays responsive | GIL issues possible |

**My recommendation:** Synchronous for Phase 1. Streamlit has `st.spinner()` which shows "Generating..." while it waits. Good enough for a demo.

**You decide:** Sync or async?

---

### 3. Error Handling Scenarios

| Error | How to handle |
|---|---|
| Ollama not running | Clear error: "Ollama is not running. Start it with: ollama serve" |
| Model not pulled | Clear error: "Model not found. Pull it with: ollama pull gemma2:2b" |
| Model too slow | Timeout after 30s, show "Generation timed out" |
| Empty context | Tell LLM: "No relevant memories found. Say you don't have information." |

**My recommendation:** Handle all of these. The demo must not crash.

**You decide:** Any other error cases to handle?

---

### 4. Temperature / Generation Parameters

| Parameter | Value | Effect |
|---|---|---|
| Temperature | 0.1 | Very focused, deterministic |
| Temperature | 0.7 | More natural, slightly creative |
| Top-p | 0.9 | Standard nucleus sampling |
| Num predict | 256 | Max tokens to generate |

**My recommendation:** Temperature 0.1 (factual answers), num_predict 256 (short answers).

**You decide:** What generation parameters?

---

## How to Implement

Create `src/generation/llm.py`:

```python
import ollama
from src.config import Settings
from src.storage.models import MemoryRecord

def generate_answer(
    question: str,
    context_memories: list[MemoryRecord],
) -> str:
    """
    Generate a natural-language answer using retrieved memories as context.
    """
    settings = Settings()
    
    # Format context
    if not context_memories:
        context_text = "No relevant memories found."
    else:
        context_lines = [
            f"{i+1}. {mem.text}"
            for i, mem in enumerate(context_memories)
        ]
        context_text = "\n".join(context_lines)
    
    # Build prompt
    prompt = f"""You are a personal memory assistant. Answer the user's question based ONLY on the following stored memories. If the answer is not in the memories, say "I don't have that information stored."

Stored memories:
{context_text}

Question: {question}

Answer:"""
    
    # Call Ollama
    try:
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 256},
        )
        return response["message"]["content"]
    except Exception as e:
        if "connect" in str(e).lower() or "refused" in str(e).lower():
            raise ConnectionError(
                "Cannot connect to Ollama. Make sure it's running: ollama serve"
            )
        elif "not found" in str(e).lower():
            raise FileNotFoundError(
                f"Model '{settings.OLLAMA_MODEL}' not found. Pull it: ollama pull {settings.OLLAMA_MODEL}"
            )
        else:
            raise
```

---

## Verification

```bash
# First: ensure Ollama is running and model is pulled
ollama pull gemma2:2b

uv run python -c "
from src.generation.llm import generate_answer
from src.storage.models import MemoryRecord
from datetime import datetime

context = [
    MemoryRecord(text='Dentist appointment on the 14th', embedding=[], timestamp=datetime.now(), source_type='text'),
    MemoryRecord(text='Brother name is Ali', embedding=[], timestamp=datetime.now(), source_type='text'),
]
answer = generate_answer('When is my dentist appointment?', context)
print(f'Answer: {answer}')
"
```

Expected: Something like "Your dentist appointment is on the 14th."

---

## Research Notes

> _Leave your notes here as you research._

- [ ] Which prompt style? (strict / helpful / hybrid)
- [ ] Sync or async Ollama calls?
- [ ] What error cases to handle?
- [ ] What generation parameters (temperature, num_predict)?
- [ ] How to test without Ollama running?

---

## Files Changed

- `src/generation/llm.py` (new)
