from sentence_transformers import SentenceTransformer

from src.config import Settings


class Embedder:
    """Wrapper around SentenceTransformer for generating normalized semantic embeddings."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = Settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception as err:
            raise RuntimeError(
                f"Failed to load embedding model '{self.model_name}'. "
                "Ensure internet connectivity for the initial model download or verify local cache."
            ) from err

    def embed(self, text: str) -> list[float]:
        """Embed a single text string into a unit-normalized float vector."""
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple text strings in batch into unit-normalized float vectors."""
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def count_tokens(self, text: str) -> int:
        """Return the exact token count using the model tokenizer."""
        return len(self._model.tokenizer.encode(text, add_special_tokens=False))

    def tokenize(self, text: str) -> list[int]:
        """Encode text into token IDs using the model tokenizer."""
        return self._model.tokenizer.encode(text, add_special_tokens=False)

    def decode_tokens(self, token_ids: list[int]) -> str:
        """Decode a list of token IDs back into string."""
        return self._model.tokenizer.decode(token_ids, skip_special_tokens=True)
