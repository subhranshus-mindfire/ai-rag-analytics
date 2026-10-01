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
            model_name = settings.GROQ_MODEL
            if "llama" in model_name or not model_name:
                model_name = "openai/gpt-oss-120b"

            primary = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model=model_name,
                temperature=temperature,
            )
            # Automatic failover to Gemini if Groq fails
            if settings.GOOGLE_API_KEY:
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    backup = ChatGoogleGenerativeAI(
                        google_api_key=settings.GOOGLE_API_KEY,
                        model="gemini-3.8-flash",
                        temperature=temperature,
                    )
                    return primary.with_fallbacks([backup])
                except Exception:
                    pass
            return primary
        except ImportError:
            raise ImportError("langchain-groq is required for Groq. Install with `pip install langchain-groq`.")

    elif provider == "gemini":
        if not settings.GOOGLE_API_KEY:
            return _create_dummy_llm("Google API key not set in .env. Please set GOOGLE_API_KEY.")
        try:
            # Silence internal SDK AFC warning
            try:
                from google.genai.models import Models
                Models._logged_afc_warning = True
            except Exception:
                pass

            from langchain_google_genai import ChatGoogleGenerativeAI
            model_name = settings.GEMINI_MODEL
            if "2.5" in model_name or not model_name:
                model_name = "gemini-3.8-flash"

            primary = ChatGoogleGenerativeAI(
                google_api_key=settings.GOOGLE_API_KEY,
                model=model_name,
                temperature=temperature,
            )
            # Automatic failover to Groq if Gemini hits rate limits / 429
            if settings.GROQ_API_KEY:
                try:
                    from langchain_groq import ChatGroq
                    backup = ChatGroq(
                        api_key=settings.GROQ_API_KEY,
                        model=settings.GROQ_MODEL,
                        temperature=temperature,
                    )
                    return primary.with_fallbacks([backup])
                except Exception:
                    pass
            return primary
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
    """Fallback LLM for development and testing without credentials or extra libraries."""
    try:
        from langchain_core.language_models.fake import FakeListLLM
        return FakeListLLM(responses=[f"[Dev Mode: {message}]"])
    except ImportError:
        class LocalDummyLLM:
            def invoke(self, prompt: str):
                class DummyResponse:
                    content = (
                        f"[Simulated Response] Found relevant document context. "
                        f"Set your GROQ_API_KEY or GOOGLE_API_KEY in .env to get live LLM answers.\n"
                        f"Note: {message}"
                    )
                return DummyResponse()
        return LocalDummyLLM()
