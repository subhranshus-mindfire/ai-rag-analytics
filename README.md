# Enterprise GenAI Assistant: Document RAG & Text-to-SQL Analytics

A modular, production-ready enterprise assistant featuring:
1. **Document-Based RAG:** Ingests unstructured documentation (PDF, TXT, MD) and executes semantic vector retrieval with **Qdrant**.
2. **Text-to-SQL Analytics:** Relational analytics over **PostgreSQL** with safety guardrails and error-correcting agent execution.
3. **Multi-Model Support:** Free cloud LLM inference via **Groq** (`llama-3.3-70b-versatile`) or **Google AI Studio** (`gemini-2.5-flash`), with Ollama local fallback.
4. **REST API:** High-throughput async endpoints built with **FastAPI** and **Pydantic**.
5. **Containerization:** **Docker Compose** configuration for PostgreSQL and Qdrant.

---

## 📁 Project Architecture

```
.
├── docker-compose.yml        # PostgreSQL & Qdrant container definitions
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .env                      # Active runtime environment configuration
├── test_rag.py               # Standalone RAG CLI verification script
├── data/
│   ├── sql/init.sql          # Seed schema & analytics data for Text-to-SQL
│   └── docs/                 # Sample documents for RAG indexing
└── app/
    ├── main.py               # FastAPI application entrypoint & lifespan
    ├── config.py             # Settings & configuration management
    ├── core/
    │   └── llm.py            # Dynamic LLM provider factory (Groq, Gemini, Ollama)
    ├── rag/
    │   ├── loader.py         # Multi-format document loader & text chunker
    │   ├── embeddings.py     # Embedding manager (FastEmbed / HuggingFace)
    │   ├── vector_store.py   # Qdrant client wrapper (remote server & embedded mode)
    │   └── pipeline.py       # Retrieval-augmented generation coordinator
    └── api/
        ├── health.py         # System health & dependency status
        └── rag.py            # RAG query, ingestion, and upload endpoints
```

---

## 🚀 Quickstart Guide

### 1. Configure LLM API Keys
Copy `.env.example` to `.env` (already done) and set your preferred free cloud API key:

#### Option A: Groq (Recommended - Fast & Free)
1. Sign up at [https://console.groq.com/keys](https://console.groq.com/keys) (no credit card required).
2. Set in `.env`:
   ```env
   LLM_PROVIDER="groq"
   GROQ_API_KEY="your-groq-api-key"
   GROQ_MODEL="llama-3.3-70b-versatile"
   ```

#### Option B: Google Gemini API (Free Tier)
1. Get a key at [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Set in `.env`:
   ```env
   LLM_PROVIDER="gemini"
   GOOGLE_API_KEY="your-gemini-api-key"
   GEMINI_MODEL="gemini-2.5-flash"
   ```

---

### 2. Start PostgreSQL & Qdrant with Docker

```bash
docker compose up -d
```
- **PostgreSQL:** `localhost:5432` (Auto-initializes with customer & order analytics data from [init.sql](file:///home/subhranshus/Projects/AI/data/sql/init.sql))
- **Qdrant Dashboard:** `http://localhost:6333/dashboard`

---

### 3. Run the RAG Pipeline Test

Run the standalone CLI test without starting the web server:
```bash
python3 test_rag.py
```

---

### 4. Run the FastAPI Web Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** `GET http://localhost:8000/health`
- **Query Documents:** `POST http://localhost:8000/api/rag/query`
- **Upload Document:** `POST http://localhost:8000/api/rag/upload`
