import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from app.config.env_config import settings
from app.database import engine as default_engine, db_dialect as default_dialect, get_db_context

logger = logging.getLogger("DatabaseManager")


class DatabaseManager:
    """
    Manages database interaction, schema introspection, and execution.
    Can be instantiated with a custom engine or defaults to the centralized database engine.
    """

    def __init__(self, engine: Optional[Engine] = None):
        if engine is not None:
            self.engine = engine
            self.db_type = engine.dialect.name
        else:
            self.engine = default_engine
            self.db_type = default_dialect

        if self.db_type == "sqlite":
            self._seed_sqlite_if_needed()

    def _seed_sqlite_if_needed(self):
        """Initializes tables and seeds data in SQLite replica for local testing if not present."""
        try:
            inspector = inspect(self.engine)
            if "customers" in inspector.get_table_names():
                return
        except Exception:
            pass

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
