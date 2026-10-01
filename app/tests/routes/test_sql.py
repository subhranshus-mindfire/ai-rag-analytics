"""Tests for SQL Agent and Validation."""
import unittest
from app.tools.retriever_tool import sql_validator, SecurityValidationError
from app.utils.core_utils.db_utils import db_manager
from app.agents.retriever_agent import sql_agent

class TestSQLAgent(unittest.TestCase):

    def test_sql_validator_allows_valid_select(self):
        query = "SELECT id, name FROM customers WHERE segment = 'Enterprise';"
        cleaned = sql_validator.sanitize_and_validate(query)
        self.assertTrue(cleaned.startswith("SELECT"))
        self.assertFalse(cleaned.endswith(";"))

    def test_sql_validator_blocks_forbidden_mutations(self):
        forbidden_queries = [
            "DROP TABLE customers;",
            "DELETE FROM orders WHERE id = 1;",
            "UPDATE products SET price = 0;",
            "INSERT INTO customers (name) VALUES ('Hacker');",
            "ALTER TABLE orders ADD COLUMN hacked TEXT;",
            "SELECT * FROM customers; DROP TABLE orders;"
        ]
        for q in forbidden_queries:
            with self.subTest(query=q):
                with self.assertRaises(SecurityValidationError):
                    sql_validator.sanitize_and_validate(q)

    def test_database_schema_reflection(self):
        schema = db_manager.get_schema_summary()
        self.assertIn("customers", schema.lower())
        self.assertIn("orders", schema.lower())
        self.assertIn("products", schema.lower())

    def test_sql_agent_query_execution(self):
        res = sql_agent.answer_question("How many products are in the catalog?")
        self.assertIn("rows", res)
        self.assertIn("sql_query", res)
        self.assertTrue(len(res["rows"]) > 0)
        self.assertIn("latency_ms", res["logs"])

if __name__ == "__main__":
    unittest.main()
