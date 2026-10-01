from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.rag.pipeline import rag_pipeline

router = APIRouter(prefix="/documents", tags=["Documents"])

class IngestDirectoryRequest(BaseModel):
    directory_path: Optional[str] = Field(default="data/documents/", description="Directory to ingest from")

@router.post("/ingest")
def ingest_documents_endpoint(request: Optional[IngestDirectoryRequest] = None):
    """
    Ingests all supported documents (.pdf, .docx, .txt, .md) from data/documents/ into Qdrant.
    """
    dir_path = request.directory_path if request and request.directory_path else "data/documents/"
    try:
        result = rag_pipeline.ingest_directory(dir_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest documents: {str(e)}")

@router.get("")
def list_documents_endpoint():
    """
    Lists all indexed documents and their chunk counts stored in Qdrant.
    """
    try:
        docs = rag_pipeline.list_documents()
        return {
            "total_documents": len(docs),
            "total_chunks": rag_pipeline.vector_store.count(),
            "documents": docs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{document_id}")
def delete_document_endpoint(document_id: str):
    """
    Deletes all chunks associated with a specific document from Qdrant.
    """
    try:
        result = rag_pipeline.delete_document(document_id)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found in index.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
