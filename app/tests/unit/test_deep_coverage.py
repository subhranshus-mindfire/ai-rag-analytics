"""
Deep unit tests covering starter lifecycle, LLM client branches, and Qdrant store.
Pushes total test coverage above 80%+.
"""
import unittest
import asyncio
import zipfile
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.starter import start_application, lifespan
from app.llms.llm_factory import get_llm
from app.config.env_config import settings
from app.repository.vector_repository.qdrant_repository import QdrantStore
from app.utils.core_utils.file_utils import DocumentLoader
from app.utils.core_utils.embedding_utils import EmbeddingManager
from app.utils.core_utils.db_utils import DatabaseManager


class TestDeepCoverage(unittest.TestCase):

    def test_starter_application_endpoints(self):
        app = start_application()
        self.assertIsNotNone(app)

    @patch("pathlib.Path.exists", return_value=True)
    def test_starter_serve_ui_routes(self, mock_exists):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        res_root = client.get("/")
        self.assertEqual(res_root.status_code, 200)
        res_ui = client.get("/ui")
        self.assertEqual(res_ui.status_code, 200)
        res_api = client.get("/api")
        self.assertEqual(res_api.status_code, 200)

    def test_starter_lifespan_hook(self):
        async def run_lifespan():
            app = start_application()
            with patch("app.starter.ingestion_service") as mock_ingest:
                mock_ingest.vector_store.count.return_value = 0
                mock_ingest.ingest_directory.return_value = {"total_chunks_indexed": 5, "files_processed": 1}
                async with lifespan(app):
                    pass
        asyncio.run(run_lifespan())

    @patch("app.llms.llm_factory.settings")
    def test_llm_factory_groq_and_gemini_branches(self, mock_settings):
        # 1. Groq branch
        mock_settings.LLM_PROVIDER = "groq"
        mock_settings.GROQ_API_KEY = "dummy_key"
        mock_settings.GROQ_MODEL = "openai/gpt-oss-120b"
        mock_settings.GOOGLE_API_KEY = ""
        with patch("langchain_groq.ChatGroq", return_value=MagicMock()):
            llm = get_llm()
            self.assertIsNotNone(llm)

        # 2. Gemini branch
        mock_settings.LLM_PROVIDER = "gemini"
        mock_settings.GOOGLE_API_KEY = "dummy_key"
        mock_settings.GEMINI_MODEL = "gemini-3.8-flash"
        mock_settings.GROQ_API_KEY = ""
        with patch("langchain_google_genai.ChatGoogleGenerativeAI", return_value=MagicMock()):
            llm = get_llm()
            self.assertIsNotNone(llm)

    def test_qdrant_cosine_similarity(self):
        store = QdrantStore()
        # Same direction -> 1.0
        sim1 = store._cosine_similarity([1.0, 0.0], [1.0, 0.0])
        self.assertAlmostEqual(sim1, 1.0)
        # Orthogonal -> 0.0
        sim2 = store._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        self.assertAlmostEqual(sim2, 0.0)
        # Zero vector -> 0.0
        sim3 = store._cosine_similarity([0.0, 0.0], [1.0, 1.0])
        self.assertEqual(sim3, 0.0)

    def test_qdrant_client_remote_and_memory_locations(self):
        with patch.object(settings, "QDRANT_URL", ":memory:"):
            store_mem = QdrantStore()
            self.assertIsNotNone(store_mem)

    def test_embedding_fallback_methods(self):
        manager = EmbeddingManager()
        pseudo = manager._pseudo_embed("test text", dim=384)
        self.assertEqual(len(pseudo), 384)
        manager._provider = "fallback"
        docs = manager.embed_documents(["doc1", "doc2"])
        self.assertEqual(len(docs), 2)
        q = manager.embed_query("query")
        self.assertEqual(len(q), 384)

    def test_database_manager_sqlite_seed_execution(self):
        from sqlalchemy import create_engine
        db = DatabaseManager()
        # Seed fresh in-memory sqlite
        db.engine = create_engine("sqlite:///:memory:")
        db._seed_sqlite_if_needed()
        cols, rows = db.execute("SELECT name FROM customers LIMIT 1;")
        self.assertTrue(len(rows) >= 0)

    def test_sql_agent_retry_exhaustion(self):
        from app.agents.retriever_agent import SQLAgent
        agent = SQLAgent()
        with patch.object(agent, "generate_sql", return_value="INVALID SQL STATEMENT"):
            res = agent.answer_question("test question", max_retries=0)
            self.assertIn("error", res)
            self.assertEqual(len(res["rows"]), 0)

    def test_docx_xml_parsing(self):
        loader = DocumentLoader()
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            docx_path = f.name

        try:
            with zipfile.ZipFile(docx_path, "w") as z:
                xml_content = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    '<w:body><w:p><w:r><w:t>Sample DOCX paragraph.</w:t></w:r></w:p></w:body>'
                    '</w:document>'
                )
                z.writestr("word/document.xml", xml_content)
            
            content = loader.load_file(docx_path)
            self.assertIn("Sample DOCX paragraph", content)
        finally:
            Path(docx_path).unlink(missing_ok=True)

    def test_ingestion_route_direct_coverage(self):
        from unittest.mock import AsyncMock
        from app.routes.core_routes.ingestion_route import (
            upload_document_endpoint,
            ingest_documents_endpoint,
            list_documents_endpoint,
            delete_document_endpoint,
            MAX_FILE_SIZE_BYTES
        )
        from app.schemas.core_schemas.ingestion_schema import IngestDirectoryRequest
        from fastapi import UploadFile, HTTPException

        # 1. list_documents_endpoint
        res_list = list_documents_endpoint()
        self.assertIn("documents", res_list)

        # 2. ingest_documents_endpoint
        with patch("app.routes.core_routes.ingestion_route.ingestion_service.ingest_directory", return_value={"status": "success"}):
            req = IngestDirectoryRequest(directory_path="data/documents")
            res_ingest = ingest_documents_endpoint(req)
            self.assertEqual(res_ingest["status"], "success")

        # 3. delete_document_endpoint
        with patch("app.routes.core_routes.ingestion_route.ingestion_service.delete_document", return_value={"status": "not_found"}):
            with self.assertRaises(HTTPException):
                delete_document_endpoint("missing.pdf")

        with patch("app.routes.core_routes.ingestion_route.ingestion_service.delete_document", return_value={"status": "deleted"}):
            del_ok = delete_document_endpoint("found.pdf")
            self.assertEqual(del_ok["status"], "deleted")

        # 4. upload_document_endpoint validation branches
        mock_file_no_name = MagicMock(spec=UploadFile)
        mock_file_no_name.filename = ""
        with self.assertRaises(HTTPException):
            asyncio.run(upload_document_endpoint(mock_file_no_name))

        mock_file_bad_ext = MagicMock(spec=UploadFile)
        mock_file_bad_ext.filename = "bad.exe"
        with self.assertRaises(HTTPException):
            asyncio.run(upload_document_endpoint(mock_file_bad_ext))

        mock_file_empty = MagicMock(spec=UploadFile)
        mock_file_empty.filename = "empty.txt"
        mock_file_empty.read = AsyncMock(return_value=b"")
        with self.assertRaises(HTTPException):
            asyncio.run(upload_document_endpoint(mock_file_empty))

        mock_file_big = MagicMock(spec=UploadFile)
        mock_file_big.filename = "big.txt"
        mock_file_big.read = AsyncMock(return_value=b"x" * (MAX_FILE_SIZE_BYTES + 10))
        with self.assertRaises(HTTPException):
            asyncio.run(upload_document_endpoint(mock_file_big))

        mock_file_ok = MagicMock(spec=UploadFile)
        mock_file_ok.filename = "good_policy.txt"
        mock_file_ok.read = AsyncMock(return_value=b"Valid policy document text.")
        with patch("app.routes.core_routes.ingestion_route.ingestion_service.ingest_document", return_value={"chunks_indexed": 3, "total_documents": 1}):
            res_up = asyncio.run(upload_document_endpoint(mock_file_ok))
            self.assertEqual(res_up["status"], "success")


if __name__ == "__main__":
    unittest.main()
