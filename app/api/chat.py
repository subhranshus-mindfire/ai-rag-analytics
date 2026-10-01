from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.graph.router import process_chat_message

router = APIRouter(tags=["Chat"])

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

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Intelligent Conversational Agent endpoint.
    Routes queries dynamically via LangGraph between Document RAG, SQL Analytics, or Combined.
    Supports follow-up questions using session conversation history.
    """
    try:
        response = process_chat_message(
            message=request.message,
            session_id=request.session_id or "default"
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
