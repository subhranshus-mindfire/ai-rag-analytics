from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.config.env_config import settings
from app.health import router as health_router
from app.routes.core_routes.router import router as core_router
from app.services.core_services.ingestion_service import ingestion_service
from app.exceptions.handlers import app_error_handler, request_validation_handler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Auto-index documents in data/documents/ on boot
    docs_dir = Path("data/documents")
    if docs_dir.exists() and ingestion_service.vector_store.count() == 0:
        try:
            print(f"[*] Bootstrapping knowledge base from {docs_dir}...")
            res = ingestion_service.ingest_directory(str(docs_dir))
            print(f"[+] Ingestion complete: {res.get('total_chunks_indexed', 0)} chunks indexed across {res.get('files_processed', 0)} documents.")
        except Exception as e:
            print(f"[!] Warning: Auto-indexing encountered an issue: {e}")
    yield

def start_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Local GenAI Data Assistant: Multi-Format Document RAG, Text-to-SQL Analytics, and LangGraph Router",
        version="1.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(Exception, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)

    app.include_router(health_router)
    app.include_router(core_router)

    import os
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    frontend_dist = Path("frontend/dist")
    static_dir = Path("static")

    if os.path.exists("frontend/dist/assets"):
        app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    elif os.path.exists("static/assets"):
        app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    if os.path.exists("frontend/dist"):
        app.mount("/frontend", StaticFiles(directory="frontend/dist"), name="frontend")

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    def serve_ui():
        if os.path.isfile("frontend/dist/index.html"):
            return FileResponse("frontend/dist/index.html")
        index_file = Path("static/index.html")
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend static/index.html not found"}

    @app.get("/ui")
    def serve_ui_alias():
        return serve_ui()

    @app.get("/api")
    def api_endpoints_info():
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

    return app
