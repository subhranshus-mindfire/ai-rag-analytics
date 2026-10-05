"""
Unit tests covering LangGraph nodes and SQL Agent error retries.
"""
import unittest
from unittest.mock import patch, MagicMock
from app.agents.supervisor_agent import rag_node, sql_node, combined_node
from app.agents.retriever_agent import SQLAgent
from app.agents.base_agent import AgentState


class TestAgentNodesCoverage(unittest.TestCase):
    def setUp(self):
        self.sql_agent = SQLAgent()

    @patch("app.agents.supervisor_agent.retrieval_service.ask")
    def test_rag_node_execution(self, mock_ask):
        mock_ask.return_value = {"answer": "Policy answer", "sources": ["doc.txt"]}
        state: AgentState = {"question": "What is leave policy?"}
        res = rag_node(state)
        self.assertEqual(res["final_answer"], "Policy answer")
        self.assertEqual(res["sources"], ["doc.txt"])

    @patch("app.agents.supervisor_agent.sql_agent.answer_question")
    def test_sql_node_execution(self, mock_answer):
        mock_answer.return_value = {"answer": "10 customers", "logs": {"latency_ms": 5}}
        state: AgentState = {"question": "How many customers?"}
        res = sql_node(state)
        self.assertEqual(res["final_answer"], "10 customers")
        self.assertEqual(res["sql_logs"], {"latency_ms": 5})

    @patch("app.agents.supervisor_agent.get_llm")
    @patch("app.agents.supervisor_agent.sql_agent.answer_question")
    @patch("app.agents.supervisor_agent.retrieval_service.ask")
    def test_combined_node_execution(self, mock_ask, mock_sql, mock_get_llm):
        mock_ask.return_value = {"answer": "Refund policy is 30 days.", "sources": ["return.txt"]}
        mock_sql.return_value = {"answer": "5 orders refunded.", "logs": {}, "sql_query": "SELECT 1;"}

        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "Combined synthesis answer."
        mock_llm.invoke.return_value = mock_resp
        mock_get_llm.return_value = mock_llm

        state: AgentState = {"question": "What is refund policy and orders count?"}
        res = combined_node(state)
        self.assertEqual(res["final_answer"], "Combined synthesis answer.")
        self.assertEqual(res["sources"], ["return.txt"])

    @patch("app.agents.retriever_agent.get_llm")
    def test_sql_agent_generate_sql_with_feedback(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "```sql\nSELECT COUNT(*) FROM customers;\n```"
        mock_llm.invoke.return_value = mock_resp
        mock_get_llm.return_value = mock_llm

        sql = self.sql_agent.generate_sql("count customers", error_feedback="column not found")
        self.assertIn("SELECT", sql)

    def test_sql_agent_execute_and_log(self):
        res = self.sql_agent.execute_and_log("SELECT COUNT(*) AS total FROM products;")
        self.assertIn("sql", res)
        self.assertIn("rows", res)
        self.assertIn("log", res)
        self.assertIn("latency_ms", res["log"])


if __name__ == "__main__":
    unittest.main()
