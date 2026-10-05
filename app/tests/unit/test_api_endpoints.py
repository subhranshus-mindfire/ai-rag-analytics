"""
FastAPI REST API Endpoints Unit & Integration Tests.
"""
import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("database", data)
        self.assertIn("vector_store", data)

    def test_api_metadata_endpoint(self):
        res = self.client.get("/api")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("endpoints", data)
        self.assertIn("chat", data["endpoints"])
        self.assertIn("health", data["endpoints"])

    def test_ui_endpoints(self):
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        res_ui = self.client.get("/ui")
        self.assertEqual(res_ui.status_code, 200)

    def test_documents_listing(self):
        res = self.client.get("/documents")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_documents", data)
        self.assertIn("documents", data)

    def test_delete_nonexistent_document_returns_404(self):
        res = self.client.delete("/documents/non_existent_doc_12345.pdf")
        self.assertEqual(res.status_code, 404)

    def test_chat_endpoint_schema_validation(self):
        # Missing required 'message' field -> 422 Unprocessable Entity
        res = self.client.post("/chat", json={})
        self.assertEqual(res.status_code, 422)

    def test_upload_unsupported_format_rejected(self):
        res = self.client.post(
            "/documents/upload",
            files={"file": ("malicious.exe", b"malicious executable bytes", "application/octet-stream")}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported file format", res.json()["detail"])

    def test_upload_empty_file_rejected(self):
        res = self.client.post(
            "/documents/upload",
            files={"file": ("empty_policy.txt", b"", "text/plain")}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("empty", res.json()["detail"].lower())

    def test_upload_valid_document(self):
        res = self.client.post(
            "/documents/upload",
            files={"file": ("test_upload_doc.txt", b"Test company policy guidelines for remote work.", "text/plain")}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["filename"], "test_upload_doc.txt")
        self.assertGreaterEqual(data["chunks_indexed"], 1)


if __name__ == "__main__":
    unittest.main()
