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

        # Filter out hits with low relevance (< 0.40 score threshold)
        relevant_hits = [h for h in hits if h.get("score", 0) >= 0.40]

        available_docs = [d.get("source") for d in self.vector_store.list_documents() if d.get("source")]
        docs_summary = ", ".join(sorted(set(available_docs))[:5]) if available_docs else "company policies and guides"

        if not relevant_hits:
            friendly_fallback = (
                f"I couldn't find any information about that in your currently uploaded documents.\n\n"
                f"📁 **Indexed Knowledge Base:** {docs_summary}\n\n"
                "💡 **Tip:** You can upload your document (e.g. `.pdf`, `.docx`, `.txt`, `.md`) using the **Upload Document** button in the sidebar, and I'll be happy to answer questions from it!"
            )
            return {
                "question": question,
                "answer": friendly_fallback,
                "sources": [],
                "retrieved_chunks": [],
                "provider": settings.LLM_PROVIDER
            }

        context_text = "\n\n---\n\n".join(
            f"[Source: {hit['metadata'].get('source', 'Unknown')} - Score: {hit['score']:.2f}]\n{hit['content']}"
            for hit in relevant_hits
        )

        prompt = (
            "You are a helpful, accurate, and polite enterprise AI assistant.\n"
            "Answer the user's question clearly and accurately using the provided context below.\n"
            "If the answer cannot be found in the context, do NOT say 'The information is not available in the provided context'. "
            f"Instead, politely explain that details on that specific topic were not found in the current documents ({docs_summary}), "
            "and invite the user to upload the relevant file using the 'Upload Document' button in the sidebar.\n\n"
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
            "sources": list({h["metadata"].get("source", "Unknown") for h in relevant_hits}),
            "retrieved_chunks": relevant_hits,
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
