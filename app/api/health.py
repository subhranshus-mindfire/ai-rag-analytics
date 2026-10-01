from fastapi import APIRouter
from app.config import settings
from app.rag.vector_store import qdrant_store

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    """Health check endpoint verifying system services status."""
    qdrant_status = "connected" if qdrant_store.client is not None else "in-memory-fallback"
    
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "qdrant_status": qdrant_status,
        "indexed_chunks": qdrant_store.count()
    }
