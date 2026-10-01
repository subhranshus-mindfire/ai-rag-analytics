from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.core_services.ingestion_service import ingestion_service
from app.schemas.core_schemas.ingestion_schema import IngestDirectoryRequest

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/ingest")
def ingest_documents_endpoint(request: Optional[IngestDirectoryRequest] = None):
    """
    Ingests all supported documents (.pdf, .docx, .txt, .md) from data/documents/ into Qdrant.
    """
    dir_path = request.directory_path if request and request.directory_path else "data/documents/"
    try:
        result = ingestion_service.ingest_directory(dir_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest documents: {str(e)}")

@router.get("")
def list_documents_endpoint():
    """
    Lists all indexed documents and their chunk counts stored in Qdrant.
    """
    try:
        docs = ingestion_service.list_documents()
        return {
            "total_documents": len(docs),
            "total_chunks": ingestion_service.vector_store.count(),
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
        result = ingestion_service.delete_document(document_id)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found in index.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
