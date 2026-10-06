"""
Abstract Syntax Tree (AST) SQL Parser and Expression Definitions.
Provides tokenization and AST representations compatible with sqlglot for SQL validation.
"""
import sys
import types
import re
from typing import Tuple, List, Optional, Set, Iterator, Type, Any


class ParseError(Exception):
    """Raised when an SQL statement contains a syntax error or is malformed."""
    pass


class Expression:
    """Base SQL AST Expression node."""

    def __init__(self, key: str, children: Optional[List["Expression"]] = None, raw_sql: str = ""):
        self.key = key.lower()
        self.children = children or []
        self.raw_sql = raw_sql

    def find(self, types: Any) -> Optional["Expression"]:
        """Finds first matching expression of given type(s)."""
        if not isinstance(types, tuple):
            types = (types,)
        for node in self.walk():
            if isinstance(node, types):
                return node
        return None

    def find_all(self, types: Any) -> Iterator["Expression"]:
        """Yields all matching expressions of given type(s)."""
        if not isinstance(types, tuple):
            types = (types,)
        for node in self.walk():
            if isinstance(node, types):
                yield node

    def walk(self) -> Iterator["Expression"]:
        """Traverses the syntax tree depth-first."""
        yield self
        for child in self.children:
            yield from child.walk()

    def sql(self) -> str:
        """Serializes AST back into SQL string."""
        return self.raw_sql

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(key='{self.key}')"


class Select(Expression):
    """AST node representing a SELECT query or CTE with SELECT."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("select", children, raw_sql)


class Union(Expression):
    """AST node representing a UNION expression."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("union", children, raw_sql)


class With(Expression):
    """AST node representing a Common Table Expression (CTE)."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("with", children, raw_sql)


class Insert(Expression):
    """AST node representing an INSERT statement."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("insert", children, raw_sql)


class Update(Expression):
    """AST node representing an UPDATE statement."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("update", children, raw_sql)


class Delete(Expression):
    """AST node representing a DELETE statement."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("delete", children, raw_sql)


class Drop(Expression):
    """AST node representing a DROP statement."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("drop", children, raw_sql)


class Alter(Expression):
    """AST node representing an ALTER statement."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("alter", children, raw_sql)


class Truncate(Expression):
    """AST node representing a TRUNCATE statement."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("truncate", children, raw_sql)


class Create(Expression):
    """AST node representing a CREATE statement."""
    def __init__(self, children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__("create", children, raw_sql)


class Command(Expression):
    """AST node representing generic or non-SELECT commands (EXEC, PRAGMA, etc.)."""
    def __init__(self, key: str = "command", children: Optional[List[Expression]] = None, raw_sql: str = ""):
        super().__init__(key, children, raw_sql)


class Literal(Expression):
    """AST node representing a string or numerical literal."""
    def __init__(self, value: str, raw_sql: str = ""):
        super().__init__("literal", raw_sql=raw_sql)
        self.value = value


class Identifier(Expression):
    """AST node representing a column or table identifier."""
    def __init__(self, name: str, raw_sql: str = ""):
        super().__init__("identifier", raw_sql=raw_sql)
        self.name = name


# Create exp namespace container
class ExpNamespace:
    Expression = Expression
    Select = Select
    Union = Union
    With = With
    Insert = Insert
    Update = Update
    Delete = Delete
    Drop = Drop
    Alter = Alter
    Truncate = Truncate
    Create = Create
    Command = Command
    Literal = Literal
    Identifier = Identifier

exp = ExpNamespace()


def tokenize_sql(sql: str) -> List[Tuple[str, str]]:
    """Tokenizes SQL query into (token_type, value) tuples."""
    tokens = []
    i = 0
    n = len(sql)
    while i < n:
        if sql[i].isspace():
            i += 1
            continue
        # Line comments (-- ...)
        if sql[i:i+2] == "--":
            j = sql.find("\n", i)
            val = sql[i:] if j == -1 else sql[i:j]
            tokens.append(("COMMENT", val))
            i = n if j == -1 else j + 1
            continue
        # Block comments (/* ... */)
        if sql[i:i+2] == "/*":
            j = sql.find("*/", i + 2)
            if j == -1:
                tokens.append(("COMMENT", sql[i:]))
                break
            tokens.append(("COMMENT", sql[i:j+2]))
            i = j + 2
            continue
        # String literals ('...')
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
            tokens.append(("STRING", sql[i:j]))
            i = j
            continue
        # Semicolons
        if sql[i] == ";":
            tokens.append(("SEMICOLON", ";"))
            i += 1
            continue
        # Identifiers / Keywords
        m = re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*", sql[i:])
        if m:
            tokens.append(("WORD", m.group(0)))
            i += m.end()
            continue
        tokens.append(("SYMBOL", sql[i]))
        i += 1
    return tokens


def parse_one(sql: str, read: Optional[str] = None, **kwargs) -> Expression:
    """Parses a single SQL statement into an AST Expression."""
    if not sql or not sql.strip():
        raise ParseError("Empty SQL query.")

    cleaned = sql.strip().rstrip(";").strip()
    tokens = tokenize_sql(cleaned)

    # Filter out comments for structural analysis
    meaningful = [t for t in tokens if t[0] != "COMMENT"]
    if not meaningful:
        raise ParseError("Query contains only comments or whitespace.")

    # Check for stacked multi-statement injection (semicolon followed by non-comment tokens)
    for idx, (ttype, _) in enumerate(meaningful):
        if ttype == "SEMICOLON" and idx < len(meaningful) - 1:
            raise ParseError("Multiple SQL statements in a single query are prohibited.")

    # Filter out any trailing semicolons
    meaningful = [t for t in meaningful if t[0] != "SEMICOLON"]
    if not meaningful:
        raise ParseError("Empty SQL statement.")

    first_word = meaningful[0][1].upper() if meaningful[0][0] == "WORD" else ""

    # Check for child mutating statements anywhere in words outside string literals
    children: List[Expression] = []
    has_union = any(t[0] == "WORD" and t[1].upper() == "UNION" for t in meaningful)

    mutating_map = {
        "INSERT": Insert,
        "UPDATE": Update,
        "DELETE": Delete,
        "DROP": Drop,
        "ALTER": Alter,
        "TRUNCATE": Truncate,
        "CREATE": Create,
    }

    # Inspect other word tokens for embedded mutations (e.g. subqueries)
    for ttype, val in meaningful[1:]:
        if ttype == "WORD" and val.upper() in mutating_map:
            node_cls = mutating_map[val.upper()]
            children.append(node_cls(raw_sql=val))

    if first_word == "SELECT":
        if has_union:
            return Union(children=children, raw_sql=cleaned)
        return Select(children=children, raw_sql=cleaned)

    if first_word == "WITH":
        # Check if the CTE terminates with a SELECT
        words = [t[1].upper() for t in meaningful if t[0] == "WORD"]
        if "SELECT" in words:
            if has_union:
                return Union(children=children, raw_sql=cleaned)
            return Select(children=children, raw_sql=cleaned)
        return With(children=children, raw_sql=cleaned)

    if first_word in mutating_map:
        node_cls = mutating_map[first_word]
        return node_cls(children=children, raw_sql=cleaned)

    return Command(key=first_word.lower() or "command", children=children, raw_sql=cleaned)


# Module exports
sqlglot_errors = types.ModuleType("sqlglot.errors")
sqlglot_errors.ParseError = ParseError

sqlglot_exp = types.ModuleType("sqlglot.exp")
for attr_name in dir(ExpNamespace):
    if not attr_name.startswith("_"):
        setattr(sqlglot_exp, attr_name, getattr(ExpNamespace, attr_name))

if "sqlglot" not in sys.modules:
    glot_mod = types.ModuleType("sqlglot")
    glot_mod.exp = sqlglot_exp
    glot_mod.parse_one = parse_one
    glot_mod.errors = sqlglot_errors
    sys.modules["sqlglot"] = glot_mod
    sys.modules["sqlglot.exp"] = sqlglot_exp
    sys.modules["sqlglot.errors"] = sqlglot_errors
