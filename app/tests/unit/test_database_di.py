"""
Unit tests for database architecture and dependency injection.
Tests session generator, context managers, health checks,
FastAPI Depends injection, and SQLAgent dependency injection.
"""
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.database import (
    get_db,
    get_db_context,
    check_db_connection,
    close_db,
    engine,
    SessionLocal,
    Base
)
from app.utils.core_utils.db_utils import DatabaseManager, db_manager
from app.agents.retriever_agent import SQLAgent
from app.main import app


class TestDatabaseDependencyInjection(unittest.TestCase):

    def test_get_db_generator_lifecycle(self):
        """Ensures get_db yields an active Session and safely closes it."""
        gen = get_db()
        session = next(gen)
        self.assertIsInstance(session, Session)
        # Execute query with session
        result = session.execute(text("SELECT 1")).scalar()
        self.assertEqual(result, 1)
        # Finish generator to trigger finally: db.close()
        with self.assertRaises(StopIteration):
            next(gen)

    def test_get_db_context_manager(self):
        """Ensures get_db_context works cleanly inside with-statement."""
        with get_db_context() as session:
            self.assertIsInstance(session, Session)
            res = session.execute(text("SELECT 1")).scalar()
            self.assertEqual(res, 1)

    def test_check_db_connection(self):
        """Verifies database connectivity check helper."""
        healthy, dialect = check_db_connection()
        self.assertTrue(healthy)
        self.assertIn(dialect, ["postgresql", "sqlite"])

    def test_fastapi_health_endpoint_depends_injection(self):
        """Verifies /health endpoint successfully uses Depends(get_db)."""
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["database"]["status"], "connected")

    def test_fastapi_dependency_override(self):
        """Verifies FastAPI allows overriding get_db dependency for tests."""
        mock_session = MagicMock(spec=Session)
        mock_session.execute.return_value = MagicMock()

        def override_get_db():
            try:
                yield mock_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        try:
            client = TestClient(app)
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            mock_session.execute.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_sql_agent_dependency_injection(self):
        """Verifies SQLAgent accepts custom injected DatabaseManager and validator."""
        mock_db = MagicMock(spec=DatabaseManager)
        mock_db.get_schema_summary.return_value = "Table 'mock_table': id (INTEGER)"
        mock_validator = MagicMock()

        agent = SQLAgent(db=mock_db, validator=mock_validator)
        self.assertEqual(agent.db, mock_db)
        self.assertEqual(agent.validator, mock_validator)
        self.assertEqual(agent.get_schema_prompt(), "Table 'mock_table': id (INTEGER)")

    def test_database_manager_custom_engine_injection(self):
        """Verifies DatabaseManager can be constructed with an injected engine."""
        custom_engine = create_engine("sqlite:///:memory:")
        manager = DatabaseManager(engine=custom_engine)
        self.assertEqual(manager.engine, custom_engine)
        self.assertEqual(manager.db_type, "sqlite")

    def test_orm_models_and_relationships(self):
        """Verifies declarative models, relationships, and serialization."""
        from sqlalchemy.orm import sessionmaker
        from app.models.analytics_models import Customer, Product, Order, OrderItem

        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()

        try:
            # 1. Create customer
            customer = Customer(
                name="John Doe",
                email="johndoe@example.com",
                segment="Enterprise",
                country="United States"
            )
            session.add(customer)
            session.commit()
            self.assertIsNotNone(customer.id)
            self.assertEqual(customer.to_dict()["name"], "John Doe")

            # 2. Create product
            product = Product(
                name="Analytics Platform",
                category="Software",
                price=299.99,
                stock_quantity=50
            )
            session.add(product)
            session.commit()
            self.assertIsNotNone(product.id)
            self.assertEqual(product.to_dict()["category"], "Software")

            # 3. Create order with item
            order = Order(customer_id=customer.id, status="completed", total_amount=299.99)
            session.add(order)
            session.commit()

            item = OrderItem(order_id=order.id, product_id=product.id, quantity=1, unit_price=299.99)
            session.add(item)
            session.commit()

            # 4. Verify relationships
            fetched_customer = session.query(Customer).filter_by(id=customer.id).first()
            self.assertEqual(len(fetched_customer.orders), 1)
            self.assertEqual(len(fetched_customer.orders[0].items), 1)
            self.assertEqual(fetched_customer.orders[0].items[0].product.name, "Analytics Platform")
        finally:
            session.close()

    def test_run_migrations_and_seeding(self):
        """Verifies programmatic migration and seed execution."""
        from app.database import run_migrations, seed_initial_data
        # Should execute safely without throwing exceptions
        run_migrations()
        seed_initial_data()


if __name__ == "__main__":
    unittest.main()
