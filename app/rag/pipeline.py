from typing import Dict, Any, List
from pathlib import Path
from app.rag.loader import document_loader
from app.rag.embeddings import embedding_manager
from app.rag.vector_store import qdrant_store
from app.core.llm import get_llm
from app.config import settings

class RAGPipeline:
    """End-to-end Retrieval-Augmented Generation (RAG) pipeline."""

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

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Finds top_k relevant context chunks for a given query."""
        query_vector = self.embeddings.embed_query(query)
        hits = self.vector_store.search(query_vector=query_vector, top_k=top_k)
        return hits

    def ask(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """Runs full RAG cycle: retrieves context, creates prompt, and calls LLM."""
        hits = self.retrieve(question, top_k=top_k)

        if not hits:
            context_text = "No relevant context found in the database."
        else:
            context_text = "\n\n---\n\n".join(
                f"[Source: {hit['metadata'].get('source', 'Unknown')} - Score: {hit['score']:.2f}]\n{hit['content']}"
                for hit in hits
            )

        prompt = (
            "You are a helpful, accurate enterprise AI assistant. "
            "Answer the user's question strictly using the provided context below. "
            "If the answer cannot be found in the context, explicitly state that the information is unavailable.\n\n"
            f"### Context:\n{context_text}\n\n"
            f"### Question:\n{question}\n\n"
            "### Answer:"
        )

        llm = get_llm()
        
        try:
            # LangChain Chat invocation
            response = llm.invoke(prompt)
            raw_content = response.content if hasattr(response, "content") else str(response)
            answer = self._clean_content(raw_content)
        except Exception as e:
            answer = f"Error generating answer with {settings.LLM_PROVIDER}: {str(e)}"

        return {
            "question": question,
            "answer": answer,
            "sources": list({h["metadata"].get("source", "Unknown") for h in hits}),
            "retrieved_chunks": hits,
            "provider": settings.LLM_PROVIDER
        }

    def _clean_content(self, content) -> str:
        """Extract clean human-readable text from string, list of blocks, or dictionary response contents."""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
                elif hasattr(item, "text"):
                    text_parts.append(getattr(item, "text"))
            if text_parts:
                return "\n".join(text_parts).strip()
        return str(content).strip()

rag_pipeline = RAGPipeline()
