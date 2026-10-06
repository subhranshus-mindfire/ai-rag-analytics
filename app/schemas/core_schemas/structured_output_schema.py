from typing import Literal
from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    """Structured decision output for multi-agent intent routing."""
    intent: Literal["general", "rag", "sql", "combined"] = Field(
        description="The classified category for routing the inquiry: 'general', 'rag', 'sql', or 'combined'"
    )
    reasoning: str = Field(
        default="",
        description="Brief justification for why this route was selected based on user intent"
    )


class SQLQueryOutput(BaseModel):
    """Structured output for Text-to-SQL generation."""
    sql_query: str = Field(
        description="The valid, read-only PostgreSQL-compatible SELECT or WITH query"
    )
    explanation: str = Field(
        default="",
        description="Brief explanation of the logic, filters, and aggregations used in the query"
    )
