"""
SQL Security Validator with Abstract Syntax Tree (AST) Parsing.
Guarantees strictly read-only SELECT execution and thwarts injection attacks.
"""
import re
from typing import Set

try:
    import sqlglot
    from sqlglot import exp
    from sqlglot.errors import ParseError
except ImportError:
    import app.tools.sql_ast as sqlglot
    from app.tools.sql_ast import exp, ParseError


class SecurityValidationError(Exception):
    """Raised when an unsafe, non-SELECT, or malformed SQL query is detected."""
    pass


class SQLValidator:
    """
    Validates generated SQL to guarantee safe, read-only SELECT execution.
    Employs Abstract Syntax Tree (AST) parsing with sqlglot for deep syntactic analysis,
    neutralizing SQL comments, literal evasion, and stacked multi-statement injections.
    """

    _FORBIDDEN_EXPR_NAMES = [
        "Insert", "Update", "Delete", "Drop", "Alter",
        "Truncate", "TruncateTable", "Create", "Command"
    ]
    FORBIDDEN_EXPRESSIONS = tuple(
        getattr(exp, name) for name in _FORBIDDEN_EXPR_NAMES if hasattr(exp, name)
    )

    FORBIDDEN_KEYWORDS: Set[str] = {
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
        "CREATE", "REPLACE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
        "ATTACH", "DETACH", "PRAGMA", "SHUTDOWN", "SYSTEM", "INTO OUTFILE"
    }

    @classmethod
    def sanitize_and_validate(cls, raw_sql: str) -> str:
        """Cleans and verifies that a query is strictly a read-only SELECT query via AST analysis."""
        if not raw_sql or not raw_sql.strip():
            raise SecurityValidationError("Empty SQL query.")

        # 1. Strip markdown fences
        cleaned = raw_sql.strip()
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Remove trailing semicolon
        cleaned = cleaned.rstrip(";").strip()

        if not cleaned:
            raise SecurityValidationError("Empty SQL query.")

        # 2. Check for stacked multi-statements injection
        if cls._has_multiple_statements(cleaned):
            raise SecurityValidationError("Multiple SQL statements in a single query are prohibited.")

        # 3. Parse into Abstract Syntax Tree (AST)
        try:
            parsed = sqlglot.parse_one(cleaned)
        except (ParseError, Exception) as e:
            raise SecurityValidationError(f"SQL Syntax / Parsing Error: {str(e)}")

        if parsed is None:
            raise SecurityValidationError("Unable to parse SQL statement.")

        # 4. Strictly verify root expression is SELECT or UNION
        if not isinstance(parsed, (exp.Select, exp.Union)):
            name = getattr(parsed, "key", parsed.__class__.__name__).upper()
            raise SecurityValidationError(
                f"Only read-only SELECT or WITH statements are permitted (detected: '{name}')."
            )

        # 5. Deep AST Traversal: Verify NO mutating expressions anywhere in the tree (including CTEs & subqueries)
        for expr in parsed.find_all(cls.FORBIDDEN_EXPRESSIONS):
            name = getattr(expr, "key", expr.__class__.__name__).upper()
            raise SecurityValidationError(
                f"Forbidden SQL operation detected: '{name}' is prohibited."
            )

        # 6. Defense-in-depth: Inspect all non-literal words for blacklisted operational keywords
        for word in cls._extract_non_literal_words(cleaned):
            if word in cls.FORBIDDEN_KEYWORDS:
                raise SecurityValidationError(f"Forbidden SQL operation detected: '{word}' is prohibited.")

        return cleaned

    @classmethod
    def _has_multiple_statements(cls, sql: str) -> bool:
        """Detects whether multiple SQL statements are stacked via unquoted semicolons."""
        i = 0
        n = len(sql)
        in_single_quote = False
        in_double_quote = False

        while i < n:
            c = sql[i]
            # Skip line comments
            if not in_single_quote and not in_double_quote and sql[i:i+2] == "--":
                j = sql.find("\n", i)
                i = n if j == -1 else j + 1
                continue
            # Skip block comments
            if not in_single_quote and not in_double_quote and sql[i:i+2] == "/*":
                j = sql.find("*/", i + 2)
                i = n if j == -1 else j + 2
                continue
            # Handle quotes
            if c == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                i += 1
                continue
            if c == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                i += 1
                continue
            # Unquoted semicolon
            if c == ";" and not in_single_quote and not in_double_quote:
                rest = sql[i+1:].strip()
                # strip any trailing comments
                while rest.startswith("--") or rest.startswith("/*"):
                    if rest.startswith("--"):
                        j = rest.find("\n")
                        rest = "" if j == -1 else rest[j+1:].strip()
                    elif rest.startswith("/*"):
                        j = rest.find("*/")
                        rest = "" if j == -1 else rest[j+2:].strip()
                if rest:
                    return True
            i += 1
        return False

    @classmethod
    def _extract_non_literal_words(cls, sql: str) -> Set[str]:
        """Extracts all non-string-literal word tokens to prevent keyword confusion inside strings."""
        words: Set[str] = set()
        i = 0
        n = len(sql)
        while i < n:
            if sql[i].isspace():
                i += 1
                continue
            # Skip line comments
            if sql[i:i+2] == "--":
                j = sql.find("\n", i)
                i = n if j == -1 else j + 1
                continue
            # Skip block comments
            if sql[i:i+2] == "/*":
                j = sql.find("*/", i + 2)
                i = n if j == -1 else j + 2
                continue
            # Skip single-quoted string literals
            if sql[i] == "'":
                j = i + 1
                while j < n:
                    if sql[j] == "'":
                        if j + 1 < n and sql[j+1] == "'":
                            j += 2
                        else:
                            j += 1
                            break
                    else:
                        j += 1
                i = j
                continue
            # Word token
            m = re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*", sql[i:])
            if m:
                words.add(m.group(0).upper())
                i += m.end()
                continue
            i += 1
        return words


sql_validator = SQLValidator()
