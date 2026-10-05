from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path
from typing import Optional
from app.services.core_services.ingestion_service import ingestion_service
from app.schemas.core_schemas.ingestion_schema import IngestDirectoryRequest
from app.constants.app_constants import SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit

@router.post("/upload")
async def upload_document_endpoint(file: UploadFile = File(...)):
    """
    Validates and ingests an uploaded file (.pdf, .docx, .txt, .md) into Qdrant.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")
    
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
        )

    save_dir = Path("data/documents")
    save_dir.mkdir(parents=True, exist_ok=True)
    target_path = save_dir / file.filename

    # Clear previous chunks for this document if re-uploading
    ingestion_service.delete_document(file.filename)

    with open(target_path, "wb") as f:
        f.write(content)

    try:
        result = ingestion_service.ingest_document(str(target_path))
        return {
            "status": "success",
            "filename": file.filename,
            "chunks_indexed": result.get("chunks_indexed", 0),
            "total_documents": result.get("total_documents", 0),
            "message": f"Successfully indexed {result.get('chunks_indexed', 0)} chunks for '{file.filename}'."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and index document: {str(e)}")


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
    Deletes all chunks associated with a specific document from Qdrant and removes physical file from disk.
    """
    try:
        # Check and remove physical file from data/documents/ if it exists
        doc_path = Path("data/documents") / document_id
        file_existed = doc_path.exists()
        if file_existed:
            doc_path.unlink(missing_ok=True)

        result = ingestion_service.delete_document(document_id)
        if result["status"] == "not_found" and not file_existed:
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found in index.")
        return {
            "status": "deleted",
            "document_id": document_id,
            "chunks_removed": result.get("chunks_removed", 0),
            "message": f"Successfully deleted '{document_id}'."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

