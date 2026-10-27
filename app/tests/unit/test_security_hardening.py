"""
Comprehensive Security and Hardening Test Suite.
Validates remediation of:
- CWE-22 (Path Traversal & Arbitrary File Deletion)
- CWE-502 (Insecure Deserialization / Pickle Elimination)
- Unbounded Memory Leaks (BoundedSessionStore)
- SQL Prompt Flooding and Statement Row Caps
- LangGraph Unified Streaming Execution
"""
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.routes.core_routes.ingestion_route import _get_safe_document_path, DOCUMENTS_BASE_DIR
from app.agents.checkpoint_saver import SqliteSaver, _serialize_safe, _deserialize_safe
from app.agents.supervisor_agent import BoundedSessionStore, session_memory_store, process_chat_stream
from app.utils.core_utils.db_utils import db_manager
from app.agents.retriever_agent import SQLAgent


class TestSecurityHardening(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. CWE-22: Path Traversal Tests
    # -------------------------------------------------------------------------
    def test_path_traversal_directory_escape_blocked(self):
        """Verifies that path traversal sequences in document_id are blocked with 400."""
        malicious_ids = [
            "../../app/main.py",
            "../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/shadow",
            "....//....//something.txt",
            "..",
            "",
            "   "
        ]
        for malicious_id in malicious_ids:
            with self.subTest(id=malicious_id):
                response = self.client.delete(f"/documents/{malicious_id}")
                self.assertIn(response.status_code, [400, 404, 405])

    def test_safe_document_path_helper_confinement(self):
        """Verifies _get_safe_document_path confines files strictly to DOCUMENTS_BASE_DIR."""
        with self.assertRaises(Exception):
            _get_safe_document_path("../../secret.py")

        with self.assertRaises(Exception):
            _get_safe_document_path("/root/file.txt")

        # Valid clean filename is accepted
        safe_path = _get_safe_document_path("my_document.pdf")
        self.assertEqual(safe_path.name, "my_document.pdf")
        self.assertTrue(str(safe_path).startswith(str(DOCUMENTS_BASE_DIR)))

    def test_ingest_directory_traversal_blocked(self):
        """Verifies arbitrary external directories cannot be ingested."""
        response = self.client.post("/documents/ingest", json={"directory_path": "/etc"})
        self.assertIn(response.status_code, [400, 404])

    # -------------------------------------------------------------------------
    # 2. CWE-502: Safe Serialization Tests (No Pickle)
    # -------------------------------------------------------------------------
    def test_safe_serialization_format_is_json(self):
        """Verifies _serialize_safe produces clean UTF-8 JSON bytes, not pickle."""
        test_data = {"key": "value", "list": [1, 2, 3], "nested": {"a": True}}
        raw_bytes = _serialize_safe(test_data)
        self.assertTrue(raw_bytes.startswith(b"{"))
        deserialized = _deserialize_safe(raw_bytes)
        self.assertEqual(deserialized, test_data)

    def test_safe_serialization_handles_bytes_and_tuples(self):
        """Verifies serialization handles tuples and byte payloads safely without pickle."""
        complex_data = (("msgpack", b"raw_msgpack_bytes"), ("metadata", b"meta_bytes"), "checkpoint_id_123")
        raw_bytes = _serialize_safe(complex_data)
        self.assertTrue(raw_bytes.startswith(b"{"))
        restored = _deserialize_safe(raw_bytes)
        self.assertEqual(restored, complex_data)

    def test_sqlite_saver_on_demand_thread_loading(self):
        """Verifies SqliteSaver loads thread state lazily rather than loading all DB rows into memory."""
        saver = SqliteSaver(db_path=":memory:")
        self.assertEqual(len(saver._loaded_threads), 0)
        # Querying an empty thread should load lazily without error
        cfg = {"configurable": {"thread_id": "thread_test_lazy"}}
        tuple_result = saver.get_tuple(cfg)
        self.assertIsNone(tuple_result)
        self.assertIn("thread_test_lazy", saver._loaded_threads)

    # -------------------------------------------------------------------------
    # 3. Memory Leak: BoundedSessionStore Tests
    # -------------------------------------------------------------------------
    def test_bounded_session_store_lru_eviction(self):
        """Verifies BoundedSessionStore evicts oldest sessions when max_sessions is reached."""
        store = BoundedSessionStore(max_sessions=3, max_turns=5)
        store["s1"] = [{"role": "user", "content": "1"}]
        store["s2"] = [{"role": "user", "content": "2"}]
        store["s3"] = [{"role": "user", "content": "3"}]
        self.assertEqual(len(store), 3)

        # Access s1 to make it most recently used
        _ = store["s1"]

        # Insert s4 -> s2 should be evicted because s1 was recently used
        store["s4"] = [{"role": "user", "content": "4"}]
        self.assertEqual(len(store), 3)
        self.assertNotIn("s2", store)
        self.assertIn("s1", store)
        self.assertIn("s4", store)

    def test_bounded_session_store_turn_capping(self):
        """Verifies BoundedSessionStore caps the number of historical turns per session."""
        store = BoundedSessionStore(max_sessions=10, max_turns=4)
        turns = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        store["session_cap_test"] = turns
        self.assertEqual(len(store["session_cap_test"]), 4)
        self.assertEqual(store["session_cap_test"][-1]["content"], "msg 9")

    # -------------------------------------------------------------------------
    # 4. SQL Prompt Flooding & Execution Limits
    # -------------------------------------------------------------------------
    def test_db_manager_execute_caps_rows(self):
        """Verifies db_manager.execute respects max_rows and does not fetch unbounded rows."""
        cols, rows = db_manager.execute("SELECT * FROM products", max_rows=2)
        self.assertLessEqual(len(rows), 2)

    def test_sql_agent_prompt_capping(self):
        """Verifies SQLAgent caps rows interpolated into synthesis prompt."""
        agent = SQLAgent()
        large_rows = [{"id": i, "val": f"item_{i}"} for i in range(200)]
        with patch.object(agent, "execute_and_log", return_value={"sql": "SELECT * FROM test", "columns": ["id", "val"], "rows": large_rows, "log": {}}):
            with patch("app.agents.retriever_agent.get_llm") as mock_get_llm:
                mock_llm = MagicMock()
                mock_llm.invoke.return_value = "Here is the summary."
                mock_get_llm.return_value = mock_llm

                res = agent.answer_question("test summary question")
                self.assertEqual(res["answer"], "Here is the summary.")
                # Verify prompt sent to LLM had capped rows
                prompt_arg = mock_llm.invoke.call_args[0][0]
                self.assertIn("displaying first 50", prompt_arg)

    # -------------------------------------------------------------------------
    # 5. LangGraph Streaming Integration
    # -------------------------------------------------------------------------
    def test_process_chat_stream_yields_events(self):
        """Verifies streaming chat yields real-time SSE event dictionaries."""
        events = list(process_chat_stream("hi", session_id="test_stream_sec"))
        event_types = [e.get("type") for e in events]
        self.assertIn("status", event_types)
        self.assertIn("intent", event_types)
        self.assertIn("done", event_types)


if __name__ == "__main__":
    unittest.main()
