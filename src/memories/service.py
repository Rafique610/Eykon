from datetime import datetime

from src.memories.embedder import Embedder
from src.memories.models import MemoryRecord

DEFAULT_CHUNK_SIZE = 256
DEFAULT_OVERLAP = 40  # 30-50 tokens (~15%)
STRICT_UPPER_CEILING = 400


def chunk_text_by_tokens(
    text: str,
    embedder: Embedder,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    strict_ceiling: int = STRICT_UPPER_CEILING,
) -> list[tuple[str, int]]:
    """Split text into token-bounded chunks respecting average size, overlap, and strict ceiling."""
    tokens = embedder.tokenize(text)
    total_tokens = len(tokens)
    if total_tokens <= chunk_size:
        return [(text, total_tokens)]

    chunks: list[tuple[str, int]] = []
    step = max(1, chunk_size - overlap)
    start = 0
    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        if end - start > strict_ceiling:
            end = start + strict_ceiling
        chunk_tokens = tokens[start:end]
        chunk_str = embedder.decode_tokens(chunk_tokens)
        chunks.append((chunk_str, len(chunk_tokens)))
        if end == total_tokens:
            break
        start += step
    return chunks


def create_memories_from_text(
    text: str,
    embedder: Embedder | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    strict_ceiling: int = STRICT_UPPER_CEILING,
) -> list[MemoryRecord]:
    """Validate text, chunk by tokens (256 avg / 30-50 overlap / 400 max), embed, and return MemoryRecords."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Memory text cannot be empty or whitespace only")

    if embedder is None:
        embedder = Embedder()

    chunks = chunk_text_by_tokens(
        cleaned,
        embedder=embedder,
        chunk_size=chunk_size,
        overlap=overlap,
        strict_ceiling=strict_ceiling,
    )

    chunk_texts = [c[0] for c in chunks]
    embeddings = embedder.embed_batch(chunk_texts)
    now = datetime.now()
    total_chunks = len(chunks)

    records: list[MemoryRecord] = []
    for idx, ((chunk_str, token_count), embedding) in enumerate(zip(chunks, embeddings)):
        records.append(
            MemoryRecord(
                text=chunk_str,
                embedding=embedding,
                timestamp=now,
                source_type="text",
                metadata={
                    "chunk_index": idx,
                    "total_chunks": total_chunks,
                    "token_count": token_count,
                },
            )
        )
    return records


def create_memory_from_text(
    text: str,
    embedder: Embedder | None = None,
) -> MemoryRecord:
    """Validate and create a MemoryRecord (returns first chunk with metadata)."""
    records = create_memories_from_text(text, embedder=embedder)
    return records[0]

