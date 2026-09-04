# Architecture Overview — Persistent Memory App

## Core Loop

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Capture   │────▶│   Storage   │────▶│  Retrieval  │────▶│ Generation  │
│  (text in)  │     │  (SQLite)   │     │ (embedding  │     │ (Ollama +   │
│             │     │             │     │  similarity)│     │  Gemma)     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │                   │
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
  Raw text ──▶    MemoryRecord ──▶     Top-K records ──▶  Natural language
  + timestamp     (text, embedding,    + scores          answer grounded
  + source_type   timestamp, source)                     in stored memories
```

## Data Flow

### Write Path (Add Memory)
1. User types text in Streamlit UI
2. `capture/text.py` normalizes it into a `MemoryRecord`
3. `retrieval/embedder.py` generates an embedding vector (384-dim)
4. `storage/repository.py` saves the record to SQLite

### Read Path (Ask Question)
1. User types a question in Streamlit UI
2. `retrieval/embedder.py` embeds the question
3. `retrieval/search.py` computes cosine similarity against all stored embeddings
4. Top-K most similar records are returned
5. `generation/llm.py` formats a prompt with the retrieved context + question
6. Ollama (Gemma) generates a natural-language answer
7. UI shows the answer AND which memories were retrieved

## Memory Record Schema

| Field | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `text` | TEXT | The raw memory content |
| `embedding` | BLOB (JSON) | 384-float vector from sentence-transformers |
| `timestamp` | TEXT (ISO 8601) | When the memory was created |
| `source_type` | TEXT | Phase 1: always "text" (future: "audio", "video") |

## Why These Choices

| Decision | Reason |
|---|---|
| SQLite over vector DB | Scale is hundreds/low-thousands — SQLite + brute-force is simpler and faster to build |
| sentence-transformers over Ollama embeddings | More mature, faster, dedicated for this purpose |
| Streamlit over Gradio | Better for multi-page apps, more control over layout |
| Brute-force cosine similarity | At this scale, instant. No need for ANN libraries |
| JSON embedding storage | Simple, debuggable. Binary packing adds complexity for no benefit at this scale |
| Pydantic Settings | INSTRUCTIONS.md rule — never use env vars directly |
