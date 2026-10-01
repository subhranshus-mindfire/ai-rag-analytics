from typing import Optional
from app.config import settings

def get_llm(temperature: float = 0.2):
    """
    Factory function returning the configured LLM instance.
    Supports Groq, Google Gemini, Ollama, and local fallbacks.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        if not settings.GROQ_API_KEY:
            # Fallback to local mock if no API key is set yet
            return _create_dummy_llm("Groq API key not set in .env. Please set GROQ_API_KEY.")
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL,
                temperature=temperature,
            )
        except ImportError:
            raise ImportError("langchain-groq is required for Groq. Install with `pip install langchain-groq`.")

    elif provider == "gemini":
        if not settings.GOOGLE_API_KEY:
            return _create_dummy_llm("Google API key not set in .env. Please set GOOGLE_API_KEY.")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                google_api_key=settings.GOOGLE_API_KEY,
                model=settings.GEMINI_MODEL,
                temperature=temperature,
            )
        except ImportError:
            raise ImportError("langchain-google-genai is required. Install with `pip install langchain-google-genai`.")

    elif provider == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                temperature=temperature,
            )
        except ImportError:
            raise ImportError("langchain-community is required for Ollama.")

    else:
        return _create_dummy_llm(f"Unknown provider '{provider}'. Choose 'groq', 'gemini', or 'ollama'.")


def _create_dummy_llm(message: str):
    """Fallback LLM for development that provides extractive answers from context when no API key is set."""
    class LocalExtractiveLLM:
        def invoke(self, prompt: str):
            class Response:
                # Extract context block from prompt
                context_part = ""
                if "### Context:" in prompt and "### Question:" in prompt:
                    try:
                        raw_context = prompt.split("### Context:")[1].split("### Question:")[0].strip()
                        question = prompt.split("### Question:")[1].split("### Answer:")[0].strip()
                        
                        # Find the lines that best address the question
                        lines = [line.strip() for line in raw_context.split("\n") if line.strip() and not line.startswith("[Source:")]
                        q_words = set(question.lower().replace("?", "").split())
                        scored_lines = []
                        for line in lines:
                            l_words = set(line.lower().split())
                            overlap = len(q_words.intersection(l_words))
                            scored_lines.append((overlap, line))
                        scored_lines.sort(key=lambda x: x[0], reverse=True)
                        
                        top_answers = [l[1] for l in scored_lines[:2] if l[0] > 0]
                        if top_answers:
                            extracted = " ".join(top_answers)
                        else:
                            extracted = lines[0] if lines else "Information not found in context."
                    except Exception:
                        extracted = "Relevant context retrieved from documents."
                else:
                    extracted = "Document context successfully processed."

                content = (
                    f"{extracted}\n\n"
                    f"💡 *[Tip: To enable conversational LLM answers, add your free GROQ_API_KEY or GOOGLE_API_KEY in .env]*"
                )
            return Response()
    return LocalExtractiveLLM()
