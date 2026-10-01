import uuid
import math
from typing import List, Dict, Any, Optional
from app.config import settings

class QdrantStore:
    """Wrapper around Qdrant Vector DB with automatic embedded/server support."""

    def __init__(self, collection_name: Optional[str] = None):
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.client = None
        self._fallback_store = []  # In-memory fallback if Qdrant isn't running
        self._init_client()

    def _init_client(self):
        try:
            from qdrant_client import QdrantClient
            url = settings.QDRANT_URL

            if url.startswith("http://") or url.startswith("https://"):
                self.client = QdrantClient(url=url)
            elif url == ":memory:":
                self.client = QdrantClient(location=":memory:")
            else:
                self.client = QdrantClient(path=url)

        except Exception as e:
            # Graceful fallback to lightweight memory store
            self.client = None

    def ensure_collection(self, vector_size: int = 384):
        """Creates the Qdrant collection if it does not already exist."""
        if not self.client:
            return

        try:
            from qdrant_client.http import models
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
        except Exception:
            self.client = None

    def add_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: Optional[List[Dict[str, Any]]] = None):
        """Add text chunks, their embeddings, and metadata into the vector collection."""
        if not texts:
            return []

        if metadatas is None:
            metadatas = [{} for _ in texts]

        point_ids = [str(uuid.uuid4()) for _ in texts]

        if self.client:
            try:
                from qdrant_client.http import models
                vector_size = len(embeddings[0])
                self.ensure_collection(vector_size=vector_size)

                points = []
                for point_id, text, vec, meta in zip(point_ids, texts, embeddings, metadatas):
                    payload = {"content": text, **meta}
                    points.append(
                        models.PointStruct(id=point_id, vector=vec, payload=payload)
                    )

                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                return point_ids
            except Exception:
                # If remote call fails, store in local fallback
                pass

        # Fallback in-memory storage
        for point_id, text, vec, meta in zip(point_ids, texts, embeddings, metadatas):
            self._fallback_store.append({
                "id": point_id,
                "content": text,
                "vector": vec,
                "metadata": meta
            })
        return point_ids

    def search(self, query_vector: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """Search the vector database for the top_k most similar document chunks."""
        if self.client:
            try:
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=top_k
                )
                return [
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "content": hit.payload.get("content", ""),
                        "metadata": {k: v for k, v in hit.payload.items() if k != "content"}
                    }
                    for hit in hits
                ]
            except Exception:
                pass

        # Fallback cosine similarity
        results = []
        for item in self._fallback_store:
            score = self._cosine_similarity(query_vector, item["vector"])
            results.append({
                "id": item["id"],
                "score": score,
                "content": item["content"],
                "metadata": item["metadata"]
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def count(self) -> int:
        if self.client:
            try:
                res = self.client.count(collection_name=self.collection_name)
                return res.count
            except Exception:
                pass
        return len(self._fallback_store)

qdrant_store = QdrantStore()
