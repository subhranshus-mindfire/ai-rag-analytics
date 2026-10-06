"""
Core Database Configuration & Dependency Injection Layer.
Provides SQLAlchemy engine, connection pooling, SessionLocal factory,
FastAPI dependency injection (get_db), and lifecycle handlers.
"""
import logging
from pathlib import Path
from typing import Generator, Tuple
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.engine import Engine
from app.config.env_config import settings

logger = logging.getLogger("Database")
logger.setLevel(logging.INFO)

# Declarative Base for ORM models
Base = declarative_base()


def _build_engine(database_url: str) -> Tuple[Engine, str]:
    """
    Constructs an SQLAlchemy engine with production connection pooling.
    Gracefully falls back to local SQLite if PostgreSQL is unreachable.
    """
    is_sqlite = database_url.startswith("sqlite")
    
    if is_sqlite:
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True
        )
        return engine, "sqlite"

    try:
        # Attempt PostgreSQL connection
        engine = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[Database] Connected successfully to PostgreSQL.")
        return engine, engine.dialect.name
    except Exception as e:
        logger.warning(
            f"[Database] Could not connect to primary database ({settings.DATABASE_URL}): {e}. "
            "Falling back to local SQLite analytics database."
        )
        fallback_path = Path("data/sql/analytics_fallback.db")
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{fallback_path.resolve()}"
        fallback_engine = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True
        )
        return fallback_engine, "sqlite"


# Global engine and session factory
engine, db_dialect = _build_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency injection provider.
    Yields a database session and guarantees closure upon request completion.

    Usage:
        @router.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.execute(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for background tasks, CLI tools, tests, and agent execution.

    Usage:
        with get_db_context() as db:
            db.execute(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Tuple[bool, str]:
    """
    Verifies database connectivity. Returns (is_healthy, dialect_or_error).
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, engine.dialect.name
    except Exception as exc:
        return False, str(exc)


def close_db() -> None:
    """Disposes connection pool on application shutdown."""
    logger.info("[Database] Disposing database connection pool.")
    engine.dispose()


def seed_initial_data() -> None:
    """Seeds baseline data for analytics and text-to-sql if tables are empty."""
    from app.models.analytics_models import Customer, Product, Order, OrderItem
    from datetime import datetime

    with get_db_context() as db:
        try:
            if db.query(Customer).count() > 0:
                return

            logger.info("[Database] Seeding initial analytics dataset...")
            customers = [
                Customer(name="Alice Johnson", email="alice@example.com", segment="Enterprise", country="United States"),
                Customer(name="Bob Smith", email="bob@example.com", segment="SMB", country="Canada"),
                Customer(name="Charlie Brown", email="charlie@example.com", segment="Consumer", country="United Kingdom"),
                Customer(name="Diana Prince", email="diana@example.com", segment="Enterprise", country="United States"),
                Customer(name="Evan Wright", email="evan@example.com", segment="SMB", country="Germany"),
            ]
            db.add_all(customers)
            db.flush()

            products = [
                Product(name="AI Analytics Dashboard", category="Software", price=499.00, stock_quantity=100),
                Product(name="Cloud Vector Engine Pro", category="Software", price=999.00, stock_quantity=50),
                Product(name="Developer API Seat", category="Subscription", price=49.00, stock_quantity=500),
                Product(Hardware_key := "Hardware Security Key", category="Hardware", price=75.00, stock_quantity=200),
                Product(name="Enterprise Support SLA", category="Services", price=1500.00, stock_quantity=20),
            ]
            products[3].name = "Hardware Security Key"
            db.add_all(products)
            db.flush()

            orders = [
                Order(customer_id=1, order_date=datetime(2026, 9, 1, 10, 15, 0), status="completed", total_amount=1498.00),
                Order(customer_id=2, order_date=datetime(2026, 9, 5, 14, 30, 0), status="completed", total_amount=49.00),
                Order(customer_id=3, order_date=datetime(2026, 9, 12, 9, 0, 0), status="completed", total_amount=150.00),
                Order(customer_id=4, order_date=datetime(2026, 9, 18, 16, 45, 0), status="completed", total_amount=2499.00),
                Order(customer_id=1, order_date=datetime(2026, 9, 22, 11, 20, 0), status="completed", total_amount=999.00),
                Order(customer_id=5, order_date=datetime(2026, 9, 25, 13, 10, 0), status="refunded", total_amount=499.00),
                Order(customer_id=2, order_date=datetime(2026, 9, 28, 17, 0, 0), status="pending", total_amount=49.00),
            ]
            db.add_all(orders)
            db.flush()

            order_items = [
                OrderItem(order_id=1, product_id=1, quantity=1, unit_price=499.00),
                OrderItem(order_id=1, product_id=2, quantity=1, unit_price=999.00),
                OrderItem(order_id=2, product_id=3, quantity=1, unit_price=49.00),
                OrderItem(order_id=3, product_id=4, quantity=2, unit_price=75.00),
                OrderItem(order_id=4, product_id=2, quantity=1, unit_price=999.00),
                OrderItem(order_id=4, product_id=5, quantity=1, unit_price=1500.00),
                OrderItem(order_id=5, product_id=2, quantity=1, unit_price=999.00),
                OrderItem(order_id=6, product_id=1, quantity=1, unit_price=499.00),
                OrderItem(order_id=7, product_id=3, quantity=1, unit_price=49.00),
            ]
            db.add_all(order_items)
            db.commit()
            logger.info("[Database] Initial analytics data successfully seeded.")
        except Exception as e:
            db.rollback()
            logger.warning(f"[Database] Could not seed initial data: {e}")


def run_migrations() -> None:
    """Applies all pending Alembic migrations up to head and ensures seeded state."""
    from alembic.config import Config
    from alembic import command

    alembic_ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    if not alembic_ini_path.exists():
        logger.warning(f"[Database] alembic.ini not found at {alembic_ini_path}, skipping migrations.")
        return

    try:
        logger.info("[Database] Applying database migrations (alembic upgrade head)...")
        alembic_cfg = Config(str(alembic_ini_path))
        command.upgrade(alembic_cfg, "head")
        logger.info("[Database] Migrations applied successfully.")
    except Exception as e:
        logger.warning(f"[Database] Alembic upgrade encountered notice: {e}")

    # Seed baseline data
    seed_initial_data()

