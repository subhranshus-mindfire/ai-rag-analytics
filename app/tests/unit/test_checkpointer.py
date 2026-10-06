"""
Unit tests for LangGraph native state checkpointers and SQLite persistence.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from app.agents.checkpoint_saver import (
    SqliteSaver,
    get_default_checkpointer,
)
from app.agents.base_agent import add_messages, AgentState
from app.agents.supervisor_agent import (
    orchestration_graph,
    process_chat_message,
    get_session_state,
    get_session_history,
    clear_session_state,
    session_memory_store,
)


class TestLangGraphCheckpointer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_checkpoints.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_messages_reducer(self):
        # Empty/None handling
        self.assertEqual(add_messages(None, None), [])
        self.assertEqual(add_messages([{"role": "user", "content": "hi"}], None), [{"role": "user", "content": "hi"}])
        self.assertEqual(add_messages(None, [{"role": "bot", "content": "hello"}]), [{"role": "bot", "content": "hello"}])
        
        # Merging two message sequences
        m1 = [{"role": "user", "content": "turn 1"}]
        m2 = [{"role": "assistant", "content": "reply 1"}]
        merged = add_messages(m1, m2)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["content"], "turn 1")
        self.assertEqual(merged[1]["content"], "reply 1")

    def test_sqlite_saver_initialization_and_context_manager(self):
        conn_str = f"sqlite:///{self.db_path}"
        with SqliteSaver.from_conn_string(conn_str) as saver:
            self.assertIsNotNone(saver.conn)
            self.assertTrue(os.path.exists(self.db_path))

    def test_dynamic_langgraph_sqlite_import(self):
        from langgraph.checkpoint.sqlite import SqliteSaver as DynamicSqliteSaver
        self.assertEqual(DynamicSqliteSaver, SqliteSaver)

    def test_sqlite_saver_persistence_across_instances(self):
        from langgraph.graph import StateGraph, START, END

        builder = StateGraph(dict)
        builder.add_node("increment", lambda s: {"count": s.get("count", 0) + 1})
        builder.add_edge(START, "increment")
        builder.add_edge("increment", END)

        # Instance 1: write checkpoint
        saver1 = SqliteSaver.from_conn_string(self.db_path)
        graph1 = builder.compile(checkpointer=saver1)
        cfg = {"configurable": {"thread_id": "thread_persist_test"}}
        res = graph1.invoke({"count": 5}, config=cfg)
        self.assertEqual(res["count"], 6)

        # Instance 2: reload from same SQLite DB file
        saver2 = SqliteSaver.from_conn_string(self.db_path)
        graph2 = builder.compile(checkpointer=saver2)
        loaded_state = graph2.get_state(cfg)
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state.values.get("count"), 6)

        # Delete thread
        saver2.delete_thread("thread_persist_test")
        cleared_state = graph2.get_state(cfg)
        self.assertEqual(cleared_state.values, {})

    def test_safe_graph_wrapper_auto_thread_id(self):
        # Calling invoke without explicit config should extract session_id or default
        state: AgentState = {
            "session_id": "test_auto_thread",
            "messages": [{"role": "user", "content": "hi"}],
            "question": "hi",
            "intent": None,
            "rag_result": None,
            "sql_result": None,
            "final_answer": None,
            "sources": [],
            "sql_logs": None
        }
        res = orchestration_graph.invoke(state)
        self.assertIn("final_answer", res)

    def test_multi_turn_history_persistence_and_inspection(self):
        session_id = "test_multi_turn_checkpointer_thread"
        clear_session_state(session_id)

        # Turn 1
        res1 = process_chat_message("hi", session_id=session_id)
        self.assertEqual(res1["session_id"], session_id)

        # Verify state via checkpointer
        state = get_session_state(session_id)
        self.assertIn("messages", state)
        history = get_session_history(session_id)
        self.assertGreaterEqual(len(history), 2)

        # Turn 2
        res2 = process_chat_message("ok", session_id=session_id)
        history2 = get_session_history(session_id)
        self.assertGreaterEqual(len(history2), 4)

        # Purge thread
        clear_session_state(session_id)
        self.assertEqual(get_session_history(session_id), [])

    def test_get_default_checkpointer_singleton(self):
        cp1 = get_default_checkpointer()
        cp2 = get_default_checkpointer()
        self.assertIs(cp1, cp2)


if __name__ == "__main__":
    unittest.main()
