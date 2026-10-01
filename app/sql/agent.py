import time
import logging
from typing import Dict, Any, List
from app.sql.db import db_manager
from app.sql.validator import sql_validator, SecurityValidationError
from app.core.llm import get_llm
from app.config import settings

logger = logging.getLogger("SQLAgent")
logger.setLevel(logging.INFO)

class SQLAgent:
    """Natural Language to SQL Agent with schema awareness, safety validation, and self-healing."""

    def __init__(self):
        self.db = db_manager
        self.validator = sql_validator

    def get_schema_prompt(self) -> str:
        return self.db.get_schema_summary()

    def generate_sql(self, question: str, error_feedback: str = None) -> str:
        """Prompts LLM to translate natural language into a PostgreSQL-compatible SELECT query."""
        schema = self.get_schema_prompt()

        feedback_section = ""
        if error_feedback:
            feedback_section = (
                f"\n### Previous Error To Fix:\n"
                f"Your previous query produced this error: {error_feedback}\n"
                f"Please fix the query based on the exact schema above.\n"
            )

        prompt = (
            "You are an expert PostgreSQL data analyst and SQL generator. "
            "Write a single valid, read-only SELECT query to answer the question.\n\n"
            f"### Database Schema:\n{schema}\n"
            f"{feedback_section}\n"
            "### Instructions:\n"
            "- Only generate SELECT queries. Never generate DROP, DELETE, UPDATE, INSERT, or ALTER.\n"
            "- Output ONLY the executable SQL query inside a markdown codeblock (```sql ... ```).\n"
            "- Use standard joins, aggregations, and ORDER BY as appropriate.\n"
            "- Do not include explanations.\n\n"
            f"### Question:\n{question}\n\n"
            "### SQL Query:"
        )

        llm = get_llm(temperature=0.0)
        response = llm.invoke(prompt)
        raw_text = response.content if hasattr(response, "content") else str(response)

        # In case response is a list (like Gemini)
        if isinstance(raw_text, list):
            parts = [item.get("text", "") for item in raw_text if isinstance(item, dict)]
            raw_text = "\n".join(parts) if parts else str(raw_text)

        return str(raw_text)

    def execute_and_log(self, raw_sql: str) -> Dict[str, Any]:
        """Validates and executes a SQL query, recording execution metrics."""
        clean_sql = self.validator.sanitize_and_validate(raw_sql)

        start_time = time.perf_counter()
        columns, rows = self.db.execute(clean_sql)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        log_entry = {
            "query": clean_sql,
            "latency_ms": elapsed_ms,
            "row_count": len(rows),
            "db_type": self.db.db_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        logger.info(f"SQL Executed [{elapsed_ms}ms, {len(rows)} rows]: {clean_sql}")

        return {
            "sql": clean_sql,
            "columns": columns,
            "rows": rows,
            "log": log_entry
        }

    def answer_question(self, question: str, max_retries: int = 2) -> Dict[str, Any]:
        """Full SQL Agent loop: NL -> SQL -> Validation -> Execution -> Self-Healing -> Answer."""
        error_msg = None
        last_sql = ""
        exec_result = None

        for attempt in range(max_retries + 1):
            try:
                raw_sql = self.generate_sql(question, error_feedback=error_msg)
                last_sql = raw_sql
                exec_result = self.execute_and_log(raw_sql)
                break  # Successful execution
            except (SecurityValidationError, Exception) as e:
                error_msg = str(e)
                logger.warning(f"SQL Agent attempt {attempt + 1} failed: {error_msg}")
                if attempt == max_retries:
                    return {
                        "question": question,
                        "sql_query": last_sql,
                        "error": f"Failed after {max_retries} attempts: {error_msg}",
                        "answer": f"I was unable to query the database due to an error: {error_msg}",
                        "rows": [],
                        "logs": {"error": error_msg}
                    }

        # Synthesize friendly answer from rows
        rows = exec_result["rows"]
        sql_query = exec_result["sql"]
        log_entry = exec_result["log"]

        synthesis_prompt = (
            "You are a helpful business analytics assistant. "
            "Convert the SQL execution result below into a clear, concise natural language answer to the user's question.\n\n"
            f"### Question:\n{question}\n\n"
            f"### Executed SQL:\n{sql_query}\n\n"
            f"### Query Results ({len(rows)} rows):\n{rows}\n\n"
            "### Natural Answer:"
        )

        llm = get_llm(temperature=0.2)
        try:
            synth_resp = llm.invoke(synthesis_prompt)
            answer_content = synth_resp.content if hasattr(synth_resp, "content") else str(synth_resp)
            if isinstance(answer_content, list):
                parts = [p.get("text", "") for p in answer_content if isinstance(p, dict)]
                answer_content = "\n".join(parts) if parts else str(answer_content)
        except Exception as e:
            answer_content = f"Query executed successfully ({len(rows)} rows returned): {rows}"

        return {
            "question": question,
            "sql_query": sql_query,
            "answer": str(answer_content).strip(),
            "rows": rows,
            "columns": exec_result["columns"],
            "logs": log_entry
        }

sql_agent = SQLAgent()
