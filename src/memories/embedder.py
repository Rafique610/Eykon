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
