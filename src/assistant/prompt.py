from src.memories.models import MemoryRecord

DEFAULT_SYSTEM_INSTRUCTION = (
    "You are a helpful, intelligent personal memory assistant.\n"
    "Your goal is to answer the user's question by synthesizing information "
    "from the stored memories into a natural, conversational response.\n\n"
    "Guidelines:\n"
    "1. Address the user directly. Always change 'I' or 'My' in the memories to 'You' or 'Your' in your answer.\n"
    "2. Do NOT copy-paste the raw memory chunks verbatim. Rephrase them into fluent sentences.\n"
    "3. Do not hallucinate. If the answer isn't in the memories, say you don't have that information.\n\n"
    "Example 1:\n"
    "Stored memories:\n[1] I love drinking green tea in the morning.\n"
    "Question: What do I like to drink?\n"
    "Answer: You like to drink green tea in the morning.\n\n"
    "Example 2:\n"
    "Stored memories:\n[1] Winter is my favorite Season, i like the cold breeze.\n"
    "Question: Is there any memory for Winter?\n"
    "Answer: Yes, you have a memory stating that Winter is your favorite season because you enjoy the cold breeze."
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
