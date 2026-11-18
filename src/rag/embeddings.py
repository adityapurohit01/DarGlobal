"""Embedding generation service using sentence-transformers (all-MiniLM-L6-v2)."""

import logging
from typing import Union

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class EmbeddingService:
    """Singleton wrapper for lazy CPU embedding generation."""

    _instance = None
    _model = None

    def __new__(cls, model_name: str = DEFAULT_MODEL_NAME):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model_name = model_name
        return cls._instance

    @property
    def model(self):
        """Lazy-loads the SentenceTransformer model on first embedding call."""
        if EmbeddingService._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            EmbeddingService._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully.")
        return EmbeddingService._model

    def embed_text(self, text: str) -> list[float]:
        """Generates embedding for a single text string."""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generates embeddings for a batch of text strings."""
        embeddings = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()
