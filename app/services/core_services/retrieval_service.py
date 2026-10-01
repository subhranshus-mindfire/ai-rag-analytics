from typing import Dict, Any, List
from app.utils.core_utils.file_utils import document_loader
from app.utils.core_utils.embedding_utils import embedding_manager
from app.repository.vector_repository.qdrant_repository import qdrant_store
from app.llms.llm_factory import get_llm
from app.config.env_config import settings

class RetrievalService:
    def __init__(self):
        self.loader = document_loader
        self.embeddings = embedding_manager
        self.vector_store = qdrant_store

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

retrieval_service = RetrievalService()
