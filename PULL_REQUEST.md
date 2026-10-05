# Pull Request Description

## 📌 PR Title
`docs: update README with current repository architecture, Makefile tooling, and frontend guide`

---

## 📝 Overview & Summary

This pull request synchronizes the project's documentation ([`README.md`](README.md)) with the current state of the codebase. The previous documentation had an outdated view of the application layout, missing mentions of the new `Makefile` automation workflows, missing details on the React frontend, and outdated unit test command paths.

---

## 🔍 Key Changes

### 1. 🏗️ Accurate Repository Architecture Map
* Replaced the outdated directory tree with the current modular architecture layout:
  * `app/agents/` (Supervisor & Retriever agents)
  * `app/routes/core_routes/` (FastAPI routers for chat and document ingestion)
  * `app/services/core_services/` (Retrieval & Ingestion business logic)
  * `app/repository/vector_repository/` (Qdrant storage layer)
  * `app/llms/` (Multi-provider LLM factory with Groq, Gemini, and Ollama failover)
  * `app/utils/core_utils/` (Embedding, DB, and File utilities)
  * `app/tests/` (Unit, route, and accuracy benchmark suites)

### 2. ⚡ Makefile Command Documentation
* Added a dedicated command reference table documenting all available `Makefile` workflows:
  * **Development:** `make dev`, `make dev-frontend`, `make run-cli`
  * **Testing & Quality:** `make test`, `make test-verbose`, `make coverage`, `make benchmark`
  * **Docker Management:** `make docker-up`, `make docker-up-d`, `make docker-down`, `make docker-clean`
  * **Maintenance:** `make clean`

### 3. 💻 React Frontend Integration
* Added instructions for launching and building the React + Vite frontend dashboard (`frontend/` directory).
* Documented dual-service local development flow (`make dev` + `make dev-frontend`).

### 4. 🧠 Embedding & RAG Stack Clarification
* Highlighted **FastEmbed** ONNX runtime usage with `BAAI/bge-small-en-v1.5`, explaining how local CPU-based embedding generation is performed without requiring heavy PyTorch dependencies.

### 5. 🧪 Test Suite Path Correction
* Updated manual test execution instructions from outdated `tests/` paths to the current test runner (`python -m unittest discover -s app/tests -p "test_*.py"` and `scripts/check_coverage.py`).

---

## 🧪 Verification & Testing

- [x] Verified markdown formatting and links render properly.
- [x] Checked Mermaid diagram syntax in the architecture section.
- [x] Verified all documented `make` commands correspond to valid targets in `Makefile`.
- [x] Verified the directory structure accurately reflects the local project file tree.

---

## 📋 Checklist

- [x] Code / Documentation adheres to repository standards.
- [x] Branch is branched from `feature/makefile-tooling` / `dev`.
- [x] No sensitive credentials or `.env` secrets committed.
- [x] All file paths and references link to active files in the repository.
