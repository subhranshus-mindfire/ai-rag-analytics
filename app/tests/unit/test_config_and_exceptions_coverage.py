"""
Unit tests covering config, constants, prompts, handlers, exceptions, and route functions.
"""
import asyncio
import unittest
from unittest.mock import patch, MagicMock
from fastapi import Request
from app.config.log_config import setup_logger
from app.config.qdrant_config import QDRANT_HOST, QDRANT_COLLECTION
from app.constants.app_constants import SUPPORTED_EXTENSIONS, DEFAULT_CHUNK_SIZE
from app.prompts.retrieval_prompt import RETRIEVAL_PROMPT
from app.prompts.supervisor_prompt import CLASSIFIER_PROMPT, SYNTHESIS_PROMPT
from app.exceptions.domain import AppError
from app.tools.retriever_tool import SecurityValidationError
from app.exceptions.handlers import app_error_handler
from app.health import health_check
from app.routes.core_routes.chat_route import chat_endpoint
from app.routes.core_routes.ingestion_route import (
    ingest_documents_endpoint,
    list_documents_endpoint,
    delete_document_endpoint
)
from app.schemas.core_schemas.chat_schema import ChatRequest
from app.schemas.core_schemas.ingestion_schema import IngestDirectoryRequest


class TestConfigAndExceptionsCoverage(unittest.TestCase):

    def test_logger_setup(self):
        logger = setup_logger("test_custom_logger")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test_custom_logger")

    def test_constants_and_prompts_exported(self):
        self.assertIn(".txt", SUPPORTED_EXTENSIONS)
        self.assertGreater(DEFAULT_CHUNK_SIZE, 0)
        self.assertIn("{context}", RETRIEVAL_PROMPT)
        self.assertIn("sql", CLASSIFIER_PROMPT)
        self.assertIn("Document Findings", SYNTHESIS_PROMPT)
        self.assertIsNotNone(QDRANT_HOST)
        self.assertIsNotNone(QDRANT_COLLECTION)

    def test_domain_exceptions(self):
        err = AppError("Custom error", status_code=400)
        self.assertEqual(err.status_code, 400)
        self.assertEqual(str(err), "Custom error")

        sec_err = SecurityValidationError("Attack blocked")
        self.assertEqual(str(sec_err), "Attack blocked")

    def test_app_error_handler(self):
        req = MagicMock(spec=Request)
        exc = AppError("Bad request", status_code=400)
        resp = asyncio.run(app_error_handler(req, exc))
        self.assertEqual(resp.status_code, 400)

    def test_health_check_function_direct(self):
        res = health_check()
        self.assertEqual(res["status"], "healthy")
        self.assertIn("database", res)
        self.assertIn("vector_store", res)

    @patch("app.routes.core_routes.chat_route.process_chat_message")
    def test_chat_route_endpoint_direct(self, mock_process):
        mock_process.return_value = {
            "session_id": "test_s",
            "intent": "sql",
            "answer": "OK",
            "sources": [],
            "sql_query": "SELECT 1;",
            "sql_logs": {}
        }
        req = ChatRequest(message="Hello", session_id="test_s")
        resp = chat_endpoint(req)
        # Verify response dictionary or model
        intent_val = resp.get("intent") if isinstance(resp, dict) else resp.intent
        self.assertEqual(intent_val, "sql")

    @patch("app.routes.core_routes.ingestion_route.ingestion_service")
    def test_ingestion_route_endpoints_direct(self, mock_service):
        mock_service.ingest_directory.return_value = {"status": "success", "files_processed": 1}
        mock_service.list_documents.return_value = [{"document_id": "doc1"}]
        mock_service.vector_store.count.return_value = 5
        mock_service.delete_document.return_value = {"status": "deleted"}

        # 1. Ingest
        req = IngestDirectoryRequest(directory_path="data/docs")
        ing_resp = ingest_documents_endpoint(req)
        self.assertEqual(ing_resp["status"], "success")

        # 2. List
        list_resp = list_documents_endpoint()
        self.assertEqual(list_resp["total_documents"], 1)

        # 3. Delete
        del_resp = delete_document_endpoint("doc1")
        self.assertEqual(del_resp["status"], "deleted")


if __name__ == "__main__":
    unittest.main()
