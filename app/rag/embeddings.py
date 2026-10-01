import hashlib
from typing import List
from app.config import settings

class EmbeddingManager:
    """Manages embedding generation using fastembed or fallback providers."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model = None
        self._provider = None

    def _init_model(self):
        if self._model is not None:
            return

        try:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=self.model_name)
            self._provider = "fastembed"
        except ImportError:
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                self._model = HuggingFaceEmbeddings(model_name=self.model_name)
                self._provider = "langchain"
            except ImportError:
                # Deterministic pseudo-embedding for testing without heavy dependencies
                self._provider = "fallback"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of document strings."""
        self._init_model()

        if self._provider == "fastembed":
            # fastembed returns generator of numpy arrays
            return [list(embedding) for embedding in self._model.embed(texts)]
        elif self._provider == "langchain":
            return self._model.embed_documents(texts)
        else:
            return [self._pseudo_embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single search query."""
        self._init_model()

        if self._provider == "fastembed":
            return list(list(self._model.embed([text]))[0])
        elif self._provider == "langchain":
            return self._model.embed_query(text)
        else:
            return self._pseudo_embed(text)

    def _pseudo_embed(self, text: str, dim: int = 384) -> List[float]:
        """Deterministic 384-dimensional vector based on SHA-256 for offline tests."""
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Create a normalized list of floats
        vector = [(h[i % len(h)] - 128) / 128.0 for i in range(dim)]
        return vector

embedding_manager = EmbeddingManager()
