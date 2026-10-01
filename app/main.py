from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.rag.pipeline import rag_pipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Auto-index documents in data/documents/ on boot
    docs_dir = Path("data/documents")
    if docs_dir.exists() and rag_pipeline.vector_store.count() == 0:
        try:
            print(f"[*] Bootstrapping knowledge base from {docs_dir}...")
            res = rag_pipeline.ingest_directory(str(docs_dir))
            print(f"[+] Ingestion complete: {res.get('total_chunks_indexed', 0)} chunks indexed across {res.get('files_processed', 0)} documents.")
        except Exception as e:
            print(f"[!] Warning: Auto-indexing encountered an issue: {e}")
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Local GenAI Data Assistant: Multi-Format Document RAG, Text-to-SQL Analytics, and LangGraph Router",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local web clients and dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static asset directory
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Register Assignment Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(documents_router)

@app.get("/")
def serve_ui():
    """Serves the interactive web interface."""
    index_file = Path("static/index.html")
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend static/index.html not found"}

@app.get("/ui")
def serve_ui_alias():
    return serve_ui()

@app.get("/api")
def api_endpoints_info():
    """Returns metadata for all available REST endpoints."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "endpoints": {
            "ui": "GET / or GET /ui",
            "chat": "POST /chat",
            "ingest_documents": "POST /documents/ingest",
            "list_documents": "GET /documents",
            "delete_document": "DELETE /documents/{id}",
            "health": "GET /health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
