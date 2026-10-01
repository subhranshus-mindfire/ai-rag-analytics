import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "AI RAG & Analytics Assistant")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    # Embeddings & Qdrant
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "./qdrant_data")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "documents")

    # PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://ai_user:ai_password@localhost:5432/ai_analytics"
    )

settings = Settings()
