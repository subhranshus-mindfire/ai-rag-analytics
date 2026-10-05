import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.agents.supervisor_agent import process_chat_message, process_chat_stream
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


@router.post("/chat/stream")
def chat_stream_endpoint(request: ChatRequest):
    """
    Streams agent lifecycle events, operational progress steps, and token chunks via Server-Sent Events (SSE).
    """
    def event_generator():
        try:
            for event in process_chat_stream(
                message=request.message,
                session_id=request.session_id or "default"
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            err_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
