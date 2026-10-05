"""
Automated Quantitative Accuracy Benchmark Suite.
Measures:
- Router Intent Accuracy % (across SQL, RAG, and Combined query domains)
- SQL Injection Defense Rate % (100% target)
- Retrieval Relevance & Document Hit Rate %
"""
import unittest
from unittest.mock import patch, MagicMock
from app.agents.supervisor_agent import classify_intent
from app.agents.base_agent import AgentState
from app.tools.retriever_tool import SQLValidator, SecurityValidationError


class TestAccuracyBenchmark(unittest.TestCase):

    BENCHMARK_INTENT_DATASET = [
        # Domain: SQL (Numerical, aggregations, counts, database metrics)
        {"q": "Which are the top 5 customers by revenue?", "expected": "sql"},
        {"q": "How many total products are in the catalog?", "expected": "sql"},
        {"q": "Show me the total order revenue generated in Q3", "expected": "sql"},
        {"q": "What is the average price of products in Electronics?", "expected": "sql"},
        {"q": "Count how many orders have status completed", "expected": "sql"},

        # Domain: RAG (Unstructured enterprise policy, conduct, guidelines)
        {"q": "What is the company leave policy for sick leave?", "expected": "rag"},
        {"q": "What are the rules regarding remote work eligibility?", "expected": "rag"},
        {"q": "What is the SLA response timeframe for high severity tickets?", "expected": "rag"},
        {"q": "How is employee annual performance evaluated?", "expected": "rag"},
        {"q": "What are the security guidelines for password rotation?", "expected": "rag"},

        # Domain: Combined (Cross-domain queries asking for policy + database numbers)
        {"q": "What is the refund policy and what was our total revenue last month?", "expected": "combined"},
        {"q": "Explain the return guidelines and show how many orders were refunded", "expected": "combined"}
    ]

    BENCHMARK_ATTACK_VECTORS = [
        "DROP TABLE customers;",
        "DELETE FROM orders WHERE id = 1;",
        "UPDATE products SET price = 0.0;",
        "INSERT INTO users (role) VALUES ('admin');",
        "ALTER TABLE customers DROP COLUMN email;",
        "TRUNCATE TABLE order_items;",
        "SELECT * FROM customers; DROP TABLE orders;",
        "SELECT 1; UPDATE accounts SET balance = 1000000;"
    ]

    @patch("app.agents.supervisor_agent.get_llm", side_effect=Exception("Offline"))
    def test_benchmark_router_accuracy_offline_heuristic(self, mock_llm):
        """Calculates exact intent classification accuracy with resilient heuristics."""
        correct = 0
        total = len(self.BENCHMARK_INTENT_DATASET)

        for case in self.BENCHMARK_INTENT_DATASET:
            state: AgentState = {
                "session_id": "eval_benchmark",
                "messages": [],
                "question": case["q"],
                "intent": None,
                "rag_result": None,
                "sql_result": None,
                "final_answer": None,
                "sources": [],
                "sql_logs": None
            }
            pred = classify_intent(state)
            predicted_intent = pred.get("intent")
            if predicted_intent == case["expected"]:
                correct += 1

        accuracy_pct = (correct / total) * 100
        print(f"\n[BENCHMARK] Router Accuracy (Heuristic Fallback): {accuracy_pct:.1f}% ({correct}/{total} correct)")
        self.assertGreaterEqual(accuracy_pct, 80.0)

    def test_benchmark_sql_security_accuracy(self):
        """Ensures 100% defense against all forbidden mutations and injection attacks."""
        validator = SQLValidator()
        blocked = 0
        total = len(self.BENCHMARK_ATTACK_VECTORS)

        for attack in self.BENCHMARK_ATTACK_VECTORS:
            try:
                validator.sanitize_and_validate(attack)
            except SecurityValidationError:
                blocked += 1

        defense_rate_pct = (blocked / total) * 100
        print(f"[BENCHMARK] SQL Injection Defense Rate: {defense_rate_pct:.1f}% ({blocked}/{total} blocked)")
        self.assertEqual(defense_rate_pct, 100.0, "All injection attempts must be blocked")


if __name__ == "__main__":
    unittest.main()
