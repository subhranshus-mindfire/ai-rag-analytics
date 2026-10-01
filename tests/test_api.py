"""Integration tests for all required FastAPI endpoints."""
import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_get_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("database", data)
        self.assertIn("vector_store", data)

    def test_documents_lifecycle(self):
        # 1. Ingest
        ingest_res = self.client.post("/documents/ingest")
        self.assertEqual(ingest_res.status_code, 200)
        self.assertGreater(ingest_res.json()["files_processed"], 0)

        # 2. List
        list_res = self.client.get("/documents")
        self.assertEqual(list_res.status_code, 200)
        docs = list_res.json()["documents"]
        self.assertGreater(len(docs), 0)

        # 3. Delete specific document
        doc_to_delete = docs[0]["document_id"]
        del_res = self.client.delete(f"/documents/{doc_to_delete}")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["status"], "deleted")

    def test_chat_sql_intent(self):
        response = self.client.post("/chat", json={
            "message": "Which are the top 5 customers by revenue?",
            "session_id": "test_session_sql"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "sql")
        self.assertIsNotNone(data["sql_query"])
        self.assertTrue(len(data["answer"]) > 0)

    def test_chat_rag_intent(self):
        response = self.client.post("/chat", json={
            "message": "What is the company leave policy?",
            "session_id": "test_session_rag"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "rag")
        self.assertTrue(len(data["answer"]) > 0)

if __name__ == "__main__":
    unittest.main()
