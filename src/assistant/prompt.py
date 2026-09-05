from src.memories.models import MemoryRecord

DEFAULT_SYSTEM_INSTRUCTION = (
    "You are a personal memory assistant. Answer the user's question based ONLY on the "
    "following stored memories. If the answer is not in the memories, say "
    "\"I don't have that information stored.\" Be concise, factual, and direct."
)


def build_rag_prompt(
    question: str,
    context_memories: list[MemoryRecord],
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
) -> str:
    """Format retrieved memory records and question into a grounded RAG prompt."""
    if not context_memories:
        context_block = "No relevant memories found."
    else:
        context_lines = [
            f"[{i+1}] {mem.text}"
            for i, mem in enumerate(context_memories)
        ]
        context_block = "\n".join(context_lines)

    prompt = (
        f"{system_instruction}\n\n"
        f"Stored memories:\n"
        f"{context_block}\n\n"
        f"Question: {question.strip()}\n\n"
        f"Answer:"
    )
    return prompt
