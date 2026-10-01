from fastapi import APIRouter, HTTPException
from app.agents.supervisor_agent import process_chat_message
from app.schemas.core_schemas.chat_schema import ChatRequest, ChatResponse

router = APIRouter(tags=["Chat"])

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
