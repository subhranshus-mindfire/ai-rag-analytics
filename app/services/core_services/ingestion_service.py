from typing import Dict, Any, List
from pathlib import Path
from app.utils.core_utils.file_utils import document_loader
from app.utils.core_utils.embedding_utils import embedding_manager
from app.repository.vector_repository.qdrant_repository import qdrant_store

class IngestionService:
    def __init__(self):
        self.loader = document_loader
        self.embeddings = embedding_manager
        self.vector_store = qdrant_store

    def ingest_document(self, file_path: str) -> Dict[str, Any]:
        """Ingests, chunks, embeds, and stores a document in Qdrant."""
        path = Path(file_path)
        content = self.loader.load_file(str(path))
        
        chunks = self.loader.chunk_text(
            text=content,
            metadata={"source": path.name, "path": str(path)}
        )

        if not chunks:
            return {"status": "empty", "chunks_indexed": 0, "source": path.name}

        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # Generate embeddings
        vectors = self.embeddings.embed_documents(texts)

        # Store in Qdrant
        point_ids = self.vector_store.add_documents(
            texts=texts,
            embeddings=vectors,
            metadatas=metadatas
        )

        return {
            "status": "success",
            "source": path.name,
            "chunks_indexed": len(point_ids),
            "total_documents": self.vector_store.count()
        }

    def ingest_directory(self, directory_path: str = "data/documents/") -> Dict[str, Any]:
        """Bulk ingests all supported documents in a directory."""
        files = self.loader.list_supported_files(directory_path)
        ingested = []
        total_chunks = 0
        for f in files:
            res = self.ingest_document(str(f))
            ingested.append(res)
            total_chunks += res.get("chunks_indexed", 0)
        return {
            "status": "success",
            "files_processed": len(files),
            "total_chunks_indexed": total_chunks,
            "results": ingested
        }

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents in the vector database."""
        return self.vector_store.list_documents()

    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete an indexed document by source name or id."""
        deleted = self.vector_store.delete_document(document_id)
        return {
            "status": "deleted" if deleted > 0 else "not_found",
            "document_id": document_id,
            "chunks_removed": deleted
        }

ingestion_service = IngestionService()
