from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config.env_config import settings
from app.repository.vector_repository.qdrant_repository import qdrant_store
from app.database import get_db
from app.utils.core_utils.db_utils import db_manager

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """System health check verifying API, Qdrant, PostgreSQL, and LLM configuration."""
    qdrant_status = "connected" if qdrant_store.client is not None else "in-memory"

    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "database": {
            "status": db_status,
            "type": db_manager.db_type,
        },
        "vector_store": {
            "status": qdrant_status,
            "collection": settings.QDRANT_COLLECTION_NAME,
            "total_chunks": qdrant_store.count()
        },
        "total_documents_indexed": len(qdrant_store.list_documents())
    }
