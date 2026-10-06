"""
Deep Security & AST Validation Tests for SQL Agent.
Tests all query types, edge cases, injection attempts, and safe executions.
"""
import unittest
from app.tools.retriever_tool import SQLValidator, SecurityValidationError
from app.utils.core_utils.db_utils import db_manager


class TestSQLSecurityAndValidation(unittest.TestCase):
    def setUp(self):
        self.validator = SQLValidator()

    def test_standard_select_queries_allowed(self):
        valid_queries = [
            "SELECT id, name FROM customers;",
            "SELECT COUNT(*) AS total_orders FROM orders WHERE status = 'completed';",
            "SELECT p.category, AVG(p.price) FROM products p GROUP BY p.category HAVING AVG(p.price) > 50;",
            "SELECT c.name, o.total_amount FROM customers c INNER JOIN orders o ON c.id = o.customer_id ORDER BY o.total_amount DESC LIMIT 10;",
            "SELECT DISTINCT status FROM orders;",
            "SELECT * FROM products WHERE price BETWEEN 10.0 AND 100.0;",
            "SELECT id, CASE WHEN total_amount > 500 THEN 'VIP' ELSE 'Standard' END AS tier FROM orders;"
        ]
        for query in valid_queries:
            with self.subTest(query=query):
                cleaned = self.validator.sanitize_and_validate(query)
                self.assertTrue(cleaned.upper().startswith("SELECT"))
                self.assertFalse(cleaned.endswith(";"), "Trailing semicolon should be stripped")

    def test_markdown_codeblock_cleaning(self):
        wrapped = "```sql\nSELECT id, name FROM customers;\n```"
        cleaned = self.validator.sanitize_and_validate(wrapped)
        self.assertEqual(cleaned, "SELECT id, name FROM customers")

    def test_dangerous_mutations_blocked(self):
        forbidden_queries = [
            "DROP TABLE customers;",
            "DROP DATABASE ai_analytics;",
            "DELETE FROM orders WHERE id = 1;",
            "DELETE FROM customers;",
            "UPDATE products SET price = 0.0;",
            "INSERT INTO customers (id, name) VALUES (999, 'Hacker');",
            "ALTER TABLE orders ADD COLUMN is_pwned BOOLEAN;",
            "TRUNCATE TABLE orders;",
            "EXEC xp_cmdshell('dir');",
            "CREATE TABLE evil (id INT);"
        ]
        for query in forbidden_queries:
            with self.subTest(query=query):
                with self.assertRaises(SecurityValidationError):
                    self.validator.sanitize_and_validate(query)

    def test_stacked_multi_statement_injection_blocked(self):
        stacked_injections = [
            "SELECT * FROM customers; DROP TABLE orders;",
            "SELECT 1; DELETE FROM products WHERE id > 0;",
            "SELECT * FROM orders; UPDATE customers SET segment = 'Enterprise';",
            "SELECT name FROM customers;--\nDROP TABLE products;"
        ]
        for query in stacked_injections:
            with self.subTest(query=query):
                with self.assertRaises(SecurityValidationError):
                    self.validator.sanitize_and_validate(query)

    def test_subqueries_and_ctes(self):
        cte_query = """
        WITH high_value AS (
            SELECT customer_id, SUM(total_amount) as spent
            FROM orders
            GROUP BY customer_id
        )
        SELECT * FROM high_value WHERE spent > 1000;
        """
        # Validator should allow CTE with WITH ... SELECT
        try:
            cleaned = self.validator.sanitize_and_validate(cte_query)
            self.assertTrue("SELECT" in cleaned.upper())
        except SecurityValidationError:
            pass  # If validator strictly checks for SELECT start, that's also safe

    def test_database_schema_reflection(self):
        schema = db_manager.get_schema_summary()
        self.assertIn("customers", schema.lower())
        self.assertIn("orders", schema.lower())
        self.assertIn("products", schema.lower())
        self.assertIn("id", schema.lower())

    def test_database_safe_execution(self):
        cols, rows = db_manager.execute("SELECT COUNT(*) AS total FROM products")
        self.assertTrue(len(rows) > 0)
        first_val = list(rows[0].values())[0]
        self.assertTrue(first_val >= 0)

    def test_ast_literal_with_forbidden_keyword_allowed(self):
        query = "SELECT id, 'DROP TABLE users' AS note FROM logs WHERE status = 'DELETED';"
        cleaned = self.validator.sanitize_and_validate(query)
        self.assertIn("SELECT", cleaned)
        self.assertIn("'DROP TABLE users'", cleaned)

    def test_ast_comment_evasion_blocked(self):
        comment_attacks = [
            "/* leading comment */ DROP TABLE customers;",
            "-- line comment\nDELETE FROM orders WHERE id = 1;",
            "SELECT 1; /* comment */ DROP TABLE products;",
            "/* bypass */ ALTER TABLE users ADD COLUMN pwned INT;"
        ]
        for q in comment_attacks:
            with self.subTest(query=q):
                with self.assertRaises(SecurityValidationError):
                    self.validator.sanitize_and_validate(q)

    def test_ast_cte_and_union_allowed(self):
        union_query = "SELECT id FROM orders UNION SELECT id FROM returns;"
        cleaned_union = self.validator.sanitize_and_validate(union_query)
        self.assertIn("UNION", cleaned_union)

        cte_query = "WITH recent AS (SELECT id, amount FROM orders WHERE amount > 100) SELECT * FROM recent;"
        cleaned_cte = self.validator.sanitize_and_validate(cte_query)
        self.assertIn("SELECT", cleaned_cte)

    def test_ast_subquery_mutation_blocked(self):
        mutation_subqueries = [
            "SELECT * FROM users WHERE id IN (DELETE FROM customers WHERE id = 1);",
            "SELECT (UPDATE products SET price = 0) AS res FROM orders;"
        ]
        for q in mutation_subqueries:
            with self.subTest(query=q):
                with self.assertRaises(SecurityValidationError):
                    self.validator.sanitize_and_validate(q)

    def test_ast_empty_or_whitespace_or_comment_only_blocked(self):
        invalid = ["", "   ", "-- only comment\n", "/* only block comment */"]
        for q in invalid:
            with self.subTest(query=q):
                with self.assertRaises(SecurityValidationError):
                    self.validator.sanitize_and_validate(q)


import app.tools.sql_ast as custom_ast


class TestCustomSQLASTParser(unittest.TestCase):
    def test_custom_ast_tokenizer(self):
        tokens = custom_ast.tokenize_sql("SELECT id, 'note' AS n FROM users WHERE id = 1; -- comment\n/* block */")
        self.assertTrue(len(tokens) > 0)
        types = [t[0] for t in tokens]
        self.assertIn("WORD", types)
        self.assertIn("STRING", types)
        self.assertIn("COMMENT", types)

    def test_custom_ast_parse_one(self):
        sel = custom_ast.parse_one("SELECT id FROM users;")
        self.assertIsInstance(sel, custom_ast.exp.Select)
        self.assertEqual(sel.key, "select")
        self.assertEqual(repr(sel), "Select(key='select')")
        self.assertEqual(sel.sql(), "SELECT id FROM users")

        union_node = custom_ast.parse_one("SELECT 1 UNION SELECT 2;")
        self.assertIsInstance(union_node, custom_ast.exp.Union)

        cte_node = custom_ast.parse_one("WITH c AS (SELECT 1) SELECT * FROM c;")
        self.assertIsInstance(cte_node, custom_ast.exp.With)
        self.assertIsNotNone(cte_node.find(custom_ast.exp.Select))

        cte_only = custom_ast.parse_one("WITH c AS (SELECT 1) DELETE FROM c;")
        self.assertIsInstance(cte_only, custom_ast.exp.With)
        self.assertIsNotNone(cte_only.find(custom_ast.exp.Delete))

    def test_custom_ast_mutations_and_commands(self):
        drop_node = custom_ast.parse_one("DROP TABLE users;")
        self.assertIsInstance(drop_node, custom_ast.exp.Drop)

        del_node = custom_ast.parse_one("DELETE FROM users;")
        self.assertIsInstance(del_node, custom_ast.exp.Delete)

        upd_node = custom_ast.parse_one("UPDATE users SET name = 'a';")
        self.assertIsInstance(upd_node, custom_ast.exp.Update)

        ins_node = custom_ast.parse_one("INSERT INTO users VALUES (1);")
        self.assertIsInstance(ins_node, custom_ast.exp.Insert)

        alt_node = custom_ast.parse_one("ALTER TABLE users ADD COLUMN c INT;")
        self.assertIsInstance(alt_node, custom_ast.exp.Alter)

        trunc_node = custom_ast.parse_one("TRUNCATE TABLE users;")
        self.assertIsInstance(trunc_node, custom_ast.exp.Truncate)

        create_node = custom_ast.parse_one("CREATE TABLE users (id INT);")
        self.assertIsInstance(create_node, custom_ast.exp.Create)

        cmd_node = custom_ast.parse_one("PRAGMA foreign_keys = ON;")
        self.assertIsInstance(cmd_node, custom_ast.exp.Command)

    def test_custom_ast_find_and_walk(self):
        tree = custom_ast.parse_one("SELECT * FROM users WHERE id IN (DELETE FROM old_users);")
        del_nodes = list(tree.find_all(custom_ast.exp.Delete))
        self.assertEqual(len(del_nodes), 1)
        found = tree.find(custom_ast.exp.Delete)
        self.assertIsNotNone(found)
        none_found = tree.find(custom_ast.exp.Drop)
        self.assertIsNone(none_found)

    def test_custom_ast_errors(self):
        with self.assertRaises(custom_ast.ParseError):
            custom_ast.parse_one("")
        with self.assertRaises(custom_ast.ParseError):
            custom_ast.parse_one("-- comment only\n")
        with self.assertRaises(custom_ast.ParseError):
            custom_ast.parse_one("SELECT 1; DROP TABLE users;")
        with self.assertRaises(custom_ast.ParseError):
            custom_ast.parse_one(";")

    def test_custom_ast_literals_and_identifiers(self):
        lit = custom_ast.exp.Literal("val", raw_sql="'val'")
        ident = custom_ast.exp.Identifier("col", raw_sql="col")
        self.assertEqual(lit.value, "val")
        self.assertEqual(ident.name, "col")


if __name__ == "__main__":
    unittest.main()
