import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.rag.pipeline import rag_pipeline
from app.config import settings

router = APIRouter(prefix="/api/rag", tags=["RAG"])

class QueryRequest(BaseModel):
    question: str = Field(..., description="The user's question to answer using RAG", example="What is the refund policy?")
    top_k: int = Field(default=3, description="Number of context chunks to retrieve", ge=1, le=10)

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]
    retrieved_chunks: List[Dict[str, Any]]
    provider: str

class IngestRequest(BaseModel):
    file_path: str = Field(..., description="Relative or absolute path to document to ingest", example="data/docs/company_policies.txt")

class IngestResponse(BaseModel):
    status: str
    source: str
    chunks_indexed: int
    total_documents: int

@router.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    """Query documents using Retrieval-Augmented Generation."""
    try:
        response = rag_pipeline.ask(question=request.question, top_k=request.top_k)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest", response_model=IngestResponse)
def ingest_file(request: IngestRequest):
    """Ingest a document from local disk into the vector database."""
    try:
        result = rag_pipeline.ingest_document(request.file_path)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=IngestResponse)
async def upload_and_ingest(file: UploadFile = File(...)):
    """Upload a document (.txt, .md, .pdf) and immediately index it into Qdrant."""
    upload_dir = Path("data/docs/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / file.filename

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = rag_pipeline.ingest_document(str(destination))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {str(e)}")

@router.get("/stats")
def get_stats():
    """Get vector collection statistics."""
    return {
        "collection_name": settings.QDRANT_COLLECTION_NAME,
        "total_chunks": rag_pipeline.vector_store.count(),
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "qdrant_url": settings.QDRANT_URL
    }
