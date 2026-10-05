import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from sqlalchemy import create_engine, text, inspect
from app.config.env_config import settings

class DatabaseManager:
    """Manages database connection to PostgreSQL with fallback to SQLite."""

    def __init__(self):
        self.engine = None
        self.db_type = "unknown"
        self._init_connection()

    def _init_connection(self):
        # 1. Attempt connection using configured DATABASE_URL
        try:
            target_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            with target_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.engine = target_engine
            self.db_type = target_engine.dialect.name
            if self.db_type == "sqlite":
                self._seed_sqlite_if_needed()
            return
        except Exception:
            pass

        # 2. Resilient local fallback to SQLite database seeded with init.sql
        sqlite_path = Path("data/sql/analytics_fallback.db")
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{sqlite_path.resolve()}"
        self.engine = create_engine(sqlite_url)
        self.db_type = "sqlite"
        self._seed_sqlite_if_needed()

    def _seed_sqlite_if_needed(self):
        """Initializes tables and seeds data in SQLite replica for local testing."""
        inspector = inspect(self.engine)
        if "customers" in inspector.get_table_names():
            return

        init_sql_path = Path("data/sql/init.sql")
        if not init_sql_path.exists():
            return

        with open(init_sql_path, "r", encoding="utf-8") as f:
            raw_sql = f.read()

        # Adapt Postgres types for SQLite compatibility
        adapted_sql = re.sub(r"SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT", raw_sql, flags=re.I)
        adapted_sql = re.sub(r"NUMERIC\(\d+,\s*\d+\)", "REAL", adapted_sql, flags=re.I)
        adapted_sql = re.sub(r"TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP", adapted_sql, flags=re.I)

        statements = [s.strip() for s in adapted_sql.split(";") if s.strip()]
        with self.engine.begin() as conn:
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass

    def get_schema_summary(self) -> str:
        """Inspects all tables, columns, and types to provide schema context to the LLM."""
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        schema_lines = []

        for table in tables:
            columns = inspector.get_columns(table)
            col_strs = [f"{col['name']} ({col['type']})" for col in columns]
            schema_lines.append(f"Table '{table}': " + ", ".join(col_strs))

        return "\n".join(schema_lines)

    def execute(self, sql_query: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Executes a validated SELECT query and returns (columns, rows)."""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql_query))
            columns = list(result.keys()) if result.returns_rows else []
            rows = [dict(zip(columns, row)) for row in result.fetchall()] if result.returns_rows else []
            return columns, rows

db_manager = DatabaseManager()
