from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or command", example="Which are the top 5 customers by revenue?")
    session_id: Optional[str] = Field(default="default", description="Conversation session identifier for multi-turn history")

class ChatResponse(BaseModel):
    session_id: str
    intent: Optional[str]
    answer: str
    sources: List[str] = []
    sql_query: Optional[str] = None
    sql_logs: Optional[Dict[str, Any]] = None
