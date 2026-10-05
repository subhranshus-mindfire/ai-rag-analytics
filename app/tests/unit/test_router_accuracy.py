"""
Comprehensive Intent Classification & LangGraph Routing Unit Tests.
Tests all routing branches: 'sql', 'rag', and 'combined' plus conversational state.
Uses mocking for deterministic, sub-second execution without external network latency.
"""
import unittest
from unittest.mock import patch, MagicMock
from app.agents.supervisor_agent import (
    classify_intent,
    route_decision,
    general_node,
    session_memory_store,
    process_chat_message
)
from app.agents.base_agent import AgentState


class TestRouterAccuracyAndBranches(unittest.TestCase):

    def test_general_node_responses(self):
        # Greeting
        state_greet: AgentState = {"question": "Hii"}
        res = general_node(state_greet)
        self.assertIn("enterprise GenAI Data Assistant", res["final_answer"])
        self.assertEqual(res["sources"], [])

        # Thanks
        state_thanks: AgentState = {"question": "Thank you so much!"}
        res_thanks = general_node(state_thanks)
        self.assertIn("welcome", res_thanks["final_answer"].lower())

        # Dismissal ("Leave it")
        state_dismiss: AgentState = {"question": "Leave it"}
        res_dismiss = general_node(state_dismiss)
        self.assertIn("no problem", res_dismiss["final_answer"].lower())

        # Acknowledgment ("Okay")
        state_ack: AgentState = {"question": "Okay, got it"}
        res_ack = general_node(state_ack)
        self.assertIn("understood", res_ack["final_answer"].lower())

    def test_route_decision_function(self):
        # 1. SQL branch
        state_sql: AgentState = {"intent": "sql"}
        self.assertEqual(route_decision(state_sql), "sql_agent")

        # 2. Combined branch
        state_comb: AgentState = {"intent": "combined"}
        self.assertEqual(route_decision(state_comb), "combined_agent")

        # 3. General / Greeting branch
        state_gen: AgentState = {"intent": "general"}
        self.assertEqual(route_decision(state_gen), "general_agent")

        # 4. RAG branch (default)
        state_rag: AgentState = {"intent": "rag"}
        self.assertEqual(route_decision(state_rag), "rag_agent")

        state_none: AgentState = {"intent": None}
        self.assertEqual(route_decision(state_none), "rag_agent")

    @patch("app.agents.supervisor_agent.get_llm")
    def test_sql_intent_llm_classification(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "sql"
        mock_llm.invoke.return_value = mock_resp
        mock_get_llm.return_value = mock_llm

        state: AgentState = {
            "session_id": "test_sql",
            "messages": [],
            "question": "Which are the top 5 customers by revenue?",
            "intent": None,
            "rag_result": None,
            "sql_result": None,
            "final_answer": None,
            "sources": [],
            "sql_logs": None
        }
        res = classify_intent(state)
        self.assertEqual(res["intent"], "sql")

    @patch("app.agents.supervisor_agent.get_llm")
    def test_rag_intent_llm_classification(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "rag"
        mock_llm.invoke.return_value = mock_resp
        mock_get_llm.return_value = mock_llm

        state: AgentState = {
            "session_id": "test_rag",
            "messages": [],
            "question": "What is the company leave policy?",
            "intent": None,
            "rag_result": None,
            "sql_result": None,
            "final_answer": None,
            "sources": [],
            "sql_logs": None
        }
        res = classify_intent(state)
        self.assertEqual(res["intent"], "rag")

    @patch("app.agents.supervisor_agent.get_llm")
    def test_combined_intent_llm_classification(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "combined"
        mock_llm.invoke.return_value = mock_resp
        mock_get_llm.return_value = mock_llm

        state: AgentState = {
            "session_id": "test_comb",
            "messages": [],
            "question": "What is the refund policy and what was total revenue?",
            "intent": None,
            "rag_result": None,
            "sql_result": None,
            "final_answer": None,
            "sources": [],
            "sql_logs": None
        }
        res = classify_intent(state)
        self.assertEqual(res["intent"], "combined")

    @patch("app.agents.supervisor_agent.get_llm", side_effect=Exception("Offline"))
    def test_heuristic_fallback_when_llm_unavailable(self, mock_get_llm):
        # When LLM raises exception, heuristic fallback operates
        state_sql: AgentState = {
            "session_id": "heuristics",
            "messages": [],
            "question": "Show total revenue and orders count",
            "intent": None,
            "rag_result": None,
            "sql_result": None,
            "final_answer": None,
            "sources": [],
            "sql_logs": None
        }
        self.assertEqual(classify_intent(state_sql)["intent"], "sql")

        state_rag: AgentState = {
            "session_id": "heuristics",
            "messages": [],
            "question": "What is the PTO leave policy guideline?",
            "intent": None,
            "rag_result": None,
            "sql_result": None,
            "final_answer": None,
            "sources": [],
            "sql_logs": None
        }
        self.assertEqual(classify_intent(state_rag)["intent"], "rag")

        state_comb: AgentState = {
            "session_id": "heuristics",
            "messages": [],
            "question": "What is the return policy and total orders count?",
            "intent": None,
            "rag_result": None,
            "sql_result": None,
            "final_answer": None,
            "sources": [],
            "sql_logs": None
        }
        self.assertEqual(classify_intent(state_comb)["intent"], "combined")

        # Greeting / General heuristic tests
        for greeting_q in ["Hii", "hello there", "good morning", "thanks", "who are you", "Leave it", "never mind", "okay"]:
            state_gen: AgentState = {
                "session_id": "heuristics",
                "messages": [],
                "question": greeting_q,
                "intent": None,
                "rag_result": None,
                "sql_result": None,
                "final_answer": None,
                "sources": [],
                "sql_logs": None
            }
            self.assertEqual(classify_intent(state_gen)["intent"], "general", f"Failed for {greeting_q}")

    @patch("app.agents.supervisor_agent.get_llm")
    def test_general_intent_llm_classification(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "general"
        mock_llm.invoke.return_value = mock_resp
        mock_get_llm.return_value = mock_llm

        state: AgentState = {
            "session_id": "test_gen",
            "messages": [],
            "question": "Hi, how are you?",
            "intent": None,
            "rag_result": None,
            "sql_result": None,
            "final_answer": None,
            "sources": [],
            "sql_logs": None
        }
        res = classify_intent(state)
        self.assertEqual(res["intent"], "general")

    @patch("app.agents.supervisor_agent.orchestration_graph.invoke")
    def test_multi_turn_session_memory(self, mock_invoke):
        mock_invoke.return_value = {
            "intent": "rag",
            "final_answer": "Company provides 20 days PTO.",
            "sources": ["company_policies.txt"],
            "sql_result": None,
            "sql_logs": None
        }
        session_id = "test_memory_session_mock"
        if session_id in session_memory_store:
            del session_memory_store[session_id]

        res1 = process_chat_message("What is the leave policy?", session_id=session_id)
        self.assertEqual(res1["session_id"], session_id)
        self.assertIn(session_id, session_memory_store)
        self.assertEqual(len(session_memory_store[session_id]), 2)

        res2 = process_chat_message("Can I take it consecutively?", session_id=session_id)
        self.assertEqual(len(session_memory_store[session_id]), 4)


if __name__ == "__main__":
    unittest.main()
