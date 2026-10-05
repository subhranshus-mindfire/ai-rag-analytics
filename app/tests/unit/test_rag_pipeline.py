"""
Document Ingestion & RAG Pipeline Unit Tests.
Tests loading, chunking, embeddings, and vector store operations.
"""
import unittest
import tempfile
from pathlib import Path
from app.utils.core_utils.file_utils import DocumentLoader
from app.utils.core_utils.embedding_utils import EmbeddingManager
from app.repository.vector_repository.qdrant_repository import QdrantStore
from app.services.core_services.ingestion_service import IngestionService
from app.services.core_services.retrieval_service import RetrievalService


class TestRAGPipeline(unittest.TestCase):
    def setUp(self):
        self.loader = DocumentLoader(chunk_size=100, chunk_overlap=20)
        self.embeddings = EmbeddingManager()
        # Use isolated in-memory vector store for testing
        self.store = QdrantStore(collection_name="test_collection")

    def test_chunking_with_overlap(self):
        sample_text = (
            "Paragraph one is introducing the core company policy.\n\n"
            "Paragraph two contains specific operational rules and SLA timeframes.\n\n"
            "Paragraph three concludes with compliance details and signatures."
        )
        chunks = self.loader.chunk_text(sample_text, metadata={"source": "test.txt"})
        self.assertTrue(len(chunks) >= 2)
        for c in chunks:
            self.assertIn("text", c)
            self.assertIn("metadata", c)
            self.assertEqual(c["metadata"]["source"], "test.txt")

    def test_document_loader_txt_file(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as f:
            f.write("Line 1: Sample policy text.\nLine 2: Confidential document.")
            temp_path = f.name

        try:
            content = self.loader.load_file(temp_path)
            self.assertIn("Sample policy text", content)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_embedding_dimensions(self):
        vec = self.embeddings.embed_query("Sample search query")
        self.assertIsInstance(vec, list)
        self.assertTrue(len(vec) > 0)
        self.assertTrue(all(isinstance(float(x), float) for x in vec))

    def test_vector_store_crud_lifecycle(self):
        texts = [
            "Company employees receive 20 days of annual PTO.",
            "Database servers must be backed up daily at midnight.",
            "Critical priority SLA response time is within 1 hour."
        ]
        embeddings = self.embeddings.embed_documents(texts)
        metadatas = [
            {"source": "pto_policy.txt"},
            {"source": "it_guide.txt"},
            {"source": "sla.txt"}
        ]

        # 1. Add documents
        point_ids = self.store.add_documents(texts, embeddings, metadatas)
        self.assertEqual(len(point_ids), 3)
        self.assertTrue(self.store.count() >= 3)

        # 2. Search
        query_vec = self.embeddings.embed_query("How many days of PTO?")
        results = self.store.search(query_vec, top_k=2)
        self.assertTrue(len(results) > 0)
        self.assertIn("content", results[0])
        self.assertIn("score", results[0])

        # 3. List
        docs = self.store.list_documents()
        self.assertTrue(len(docs) >= 1)

        # 4. Delete
        deleted = self.store.delete_document("pto_policy.txt")
        self.assertTrue(deleted >= 1)


if __name__ == "__main__":
    unittest.main()
