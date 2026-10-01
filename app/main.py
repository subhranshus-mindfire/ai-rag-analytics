from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.health import router as health_router
from app.api.rag import router as rag_router
from app.rag.pipeline import rag_pipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Auto-index sample documents if collection is empty
    sample_doc = Path("data/docs/company_policies.txt")
    if sample_doc.exists() and rag_pipeline.vector_store.count() == 0:
        try:
            print(f"[*] Auto-indexing default document: {sample_doc}")
            rag_pipeline.ingest_document(str(sample_doc))
        except Exception as e:
            print(f"[!] Warning: Auto-indexing failed: {e}")
    yield
    # Shutdown logic if needed

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise GenAI Assistant: Document RAG with Qdrant, Text-to-SQL Analytics, and LangGraph",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(rag_router)

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs_url": "/docs",
        "health_url": "/health",
        "rag_query_url": "/api/rag/query"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
