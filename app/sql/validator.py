import re

class SecurityValidationError(Exception):
    """Raised when an unsafe or non-SELECT SQL query is detected."""
    pass

class SQLValidator:
    """Validates generated SQL to guarantee safe, read-only SELECT execution."""

    FORBIDDEN_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
        "CREATE", "REPLACE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
        "ATTACH", "DETACH", "PRAGMA", "SHUTDOWN", "SYSTEM", "INTO OUTFILE"
    ]

    @classmethod
    def sanitize_and_validate(cls, raw_sql: str) -> str:
        """Cleans and verifies that a query is strictly a read-only SELECT query."""
        if not raw_sql or not raw_sql.strip():
            raise SecurityValidationError("Empty SQL query.")

        # 1. Strip markdown fences
        cleaned = raw_sql.strip()
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Remove trailing semicolon
        cleaned = cleaned.rstrip(";").strip()

        # 2. Check for multiple statements (semicolon injection)
        if ";" in cleaned:
            raise SecurityValidationError("Multiple SQL statements in a single query are prohibited.")

        # 3. Must begin with SELECT or WITH (for CTEs)
        match = re.match(r"^\s*(SELECT|WITH)\b", cleaned, flags=re.I)
        if not match:
            raise SecurityValidationError("Only read-only SELECT or WITH statements are permitted.")

        # 4. Check for forbidden mutating keywords
        for keyword in cls.FORBIDDEN_KEYWORDS:
            pattern = rf"\b{keyword}\b"
            if re.search(pattern, cleaned, flags=re.I):
                raise SecurityValidationError(f"Forbidden SQL operation detected: '{keyword}' is prohibited.")

        return cleaned

sql_validator = SQLValidator()
