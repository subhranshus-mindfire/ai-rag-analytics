"""
Unit tests covering IngestionService, RetrievalService, and content cleaning.
"""
import unittest
from unittest.mock import patch, MagicMock
from app.services.core_services.ingestion_service import IngestionService
from app.services.core_services.retrieval_service import RetrievalService


class TestServicesCoverage(unittest.TestCase):
    def setUp(self):
        self.ingestion = IngestionService()
        self.retrieval = RetrievalService()

    @patch("pathlib.Path.exists", return_value=True)
    def test_ingest_document_lifecycle(self, mock_exists):
        with patch.object(self.ingestion.loader, "load_file", return_value="Sample document content"):
            res = self.ingestion.ingest_document("data/test.txt")
            self.assertEqual(res["status"], "success")
            self.assertTrue(res["chunks_indexed"] >= 1)

    @patch("pathlib.Path.exists", return_value=True)
    def test_ingest_empty_document(self, mock_exists):
        with patch.object(self.ingestion.loader, "load_file", return_value=""):
            res = self.ingestion.ingest_document("data/empty.txt")
            self.assertEqual(res["status"], "empty")

    @patch.object(IngestionService, "ingest_document", return_value={"chunks_indexed": 2})
    def test_ingest_directory(self, mock_ingest_doc):
        with patch.object(self.ingestion.loader, "list_supported_files", return_value=["f1.txt", "f2.txt"]):
            res = self.ingestion.ingest_directory("data/docs")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["files_processed"], 2)
            self.assertEqual(res["total_chunks_indexed"], 4)

    def test_list_and_delete_documents(self):
        docs = self.ingestion.list_documents()
        self.assertIsInstance(docs, list)

        del_res = self.ingestion.delete_document("test_doc.txt")
        self.assertIn("status", del_res)

    def test_retrieval_service_retrieve(self):
        hits = self.retrieval.retrieve("leave policy", top_k=2)
        self.assertIsInstance(hits, list)

    @patch("app.services.core_services.retrieval_service.get_llm")
    def test_retrieval_service_ask_with_hits(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "Answer based on policy context."
        mock_llm.invoke.return_value = mock_resp
        mock_get_llm.return_value = mock_llm

        with patch.object(self.retrieval, "retrieve", return_value=[
            {"content": "Employees get 20 days PTO.", "score": 0.95, "metadata": {"source": "pto.txt"}}
        ]):
            res = self.retrieval.ask("How many PTO days?")
            self.assertEqual(res["answer"], "Answer based on policy context.")
            self.assertIn("pto.txt", res["sources"])

    @patch("app.services.core_services.retrieval_service.get_llm")
    def test_retrieval_service_ask_no_hits(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "Information unavailable."
        mock_llm.invoke.return_value = mock_resp
        mock_get_llm.return_value = mock_llm

        with patch.object(self.retrieval, "retrieve", return_value=[]):
            res = self.retrieval.ask("Unknown policy")
            self.assertEqual(res["answer"], "Information unavailable.")

    def test_clean_content_formatting(self):
        # 1. String
        self.assertEqual(self.retrieval._clean_content("  hello world  "), "hello world")
        # 2. List of dicts (Gemini block structure)
        self.assertEqual(self.retrieval._clean_content([{"text": "block 1"}, {"text": "block 2"}]), "block 1\nblock 2")
        # 3. List of strings
        self.assertEqual(self.retrieval._clean_content(["part a", "part b"]), "part a\npart b")


if __name__ == "__main__":
    unittest.main()
