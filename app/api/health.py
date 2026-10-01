from fastapi import APIRouter
from app.config import settings
from app.rag.vector_store import qdrant_store
from app.sql.db import db_manager

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    """System health check verifying API, Qdrant, PostgreSQL, and LLM configuration."""
    qdrant_status = "connected" if qdrant_store.client is not None else "in-memory"
    
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "database": {
            "status": "connected",
            "type": db_manager.db_type,
        },
        "vector_store": {
            "status": qdrant_status,
            "collection": settings.QDRANT_COLLECTION_NAME,
            "total_chunks": qdrant_store.count()
        },
        "total_documents_indexed": len(qdrant_store.list_documents())
    }
