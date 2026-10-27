import os
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.core_services.ingestion_service import ingestion_service
from app.schemas.core_schemas.ingestion_schema import IngestDirectoryRequest
from app.constants.app_constants import SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit
DOCUMENTS_BASE_DIR = Path("data/documents").resolve()


def _get_safe_document_path(filename: str) -> Path:
    """
    Validates and sanitizes a filename, preventing directory traversal (CWE-22).
    Guarantees that the resulting path is strictly confined to DOCUMENTS_BASE_DIR.
    """
    if not filename or not filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    # Disallow direct traversal sequences
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal sequences are not allowed.")

    safe_name = Path(filename).name
    if not safe_name or safe_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    DOCUMENTS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    target_path = (DOCUMENTS_BASE_DIR / safe_name).resolve()

    # Enforce path containment
    if not str(target_path).startswith(str(DOCUMENTS_BASE_DIR)) or target_path == DOCUMENTS_BASE_DIR:
        raise HTTPException(status_code=400, detail="Path traversal attempt detected.")

    return target_path


@router.post("/upload")
async def upload_document_endpoint(file: UploadFile = File(...)):
    """
    Validates and ingests an uploaded file (.pdf, .docx, .txt, .md) into Qdrant.
    Secured against CWE-22 (path traversal) and uses non-blocking file I/O.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    target_path = _get_safe_document_path(file.filename)
    safe_filename = target_path.name

    file_ext = target_path.suffix.lower()
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

    # Clear previous chunks for this document if re-uploading
    ingestion_service.delete_document(safe_filename)

    # Non-blocking asynchronous file write
    def _write_file():
        with open(target_path, "wb") as f:
            f.write(content)

    await asyncio.to_thread(_write_file)

    try:
        result = await asyncio.to_thread(ingestion_service.ingest_document, str(target_path))
        return {
            "status": "success",
            "filename": safe_filename,
            "chunks_indexed": result.get("chunks_indexed", 0),
            "total_documents": result.get("total_documents", 0),
            "message": f"Successfully indexed {result.get('chunks_indexed', 0)} chunks for '{safe_filename}'."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and index document: {str(e)}")


@router.post("/ingest")
def ingest_documents_endpoint(request: Optional[IngestDirectoryRequest] = None):
    """
    Ingests all supported documents (.pdf, .docx, .txt, .md) from data/documents/ into Qdrant.
    Confines ingestion directory strictly within the application data path.
    """
    raw_dir = request.directory_path if request and request.directory_path else "data/documents"
    dir_path = Path(raw_dir).resolve()

    # Security boundary: must reside within project root or data directory
    project_root = Path(".").resolve()
    if not str(dir_path).startswith(str(project_root)):
        raise HTTPException(status_code=400, detail="Directory path must reside within the application root.")

    if not dir_path.exists() or not dir_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory '{raw_dir}' does not exist or is not a directory.")

    try:
        result = ingestion_service.ingest_directory(str(dir_path))
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
    Protected against CWE-22 path traversal attacks.
    """
    try:
        target_path = _get_safe_document_path(document_id)
        file_existed = target_path.exists()
        if file_existed:
            target_path.unlink(missing_ok=True)

        result = ingestion_service.delete_document(target_path.name)
        if result["status"] == "not_found" and not file_existed:
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found in index.")
        return {
            "status": "deleted",
            "document_id": target_path.name,
            "chunks_removed": result.get("chunks_removed", 0),
            "message": f"Successfully deleted '{target_path.name}'."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
