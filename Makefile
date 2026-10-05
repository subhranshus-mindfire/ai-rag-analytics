.PHONY: help run dev run-cli dev-frontend build-frontend test test-verbose coverage benchmark docker-up docker-up-d docker-down docker-restart docker-logs docker-ps docker-clean clean

# Configuration variables
PYTHON ?= ./.venv/bin/python
UVICORN ?= ./.venv/bin/uvicorn
HOST ?= 0.0.0.0
PORT ?= 8000

help: ## Show this help menu with descriptions
	@echo "=================================================================="
	@echo "🤖 GenAI Data Assistant - Automation Commands"
	@echo "=================================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo "=================================================================="

## 🚀 Local Development Commands
run: dev ## Run FastAPI backend locally with hot-reload (alias for dev)

dev: ## Run FastAPI backend locally on port 8000 (uvicorn)
	$(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload

run-cli: ## Launch interactive terminal chat interface
	$(PYTHON) chat.py

dev-frontend: ## Launch React Vite development server (hot-reload on :5173)
	npm --prefix frontend run dev

build-frontend: ## Build production React bundle into frontend/dist
	npm --prefix frontend run build

## 🧪 Testing & Quality Commands
test: ## Run the entire automated test suite (all unit and route tests)
	$(PYTHON) -m unittest discover -s app/tests -p "test_*.py"

test-verbose: ## Run test suite with verbose per-test reporting
	$(PYTHON) -m unittest discover -s app/tests -p "test_*.py" -v

coverage: ## Measure and display code statement coverage report
	$(PYTHON) scripts/check_coverage.py

benchmark: ## Run quantitative router accuracy and security benchmarks
	$(PYTHON) -m unittest app/tests/benchmark/test_accuracy_benchmark.py -v

## 🐳 Docker Container Commands
docker-up: ## Build and start all containers (API, PostgreSQL, Qdrant, Ollama)
	docker compose up --build

docker-up-d: ## Build and start all containers in detached (background) mode
	docker compose up -d --build

docker-down: ## Stop and remove all running project containers
	docker compose down

docker-restart: ## Restart all running containers
	docker compose restart

docker-logs: ## View real-time container logs (e.g. make docker-logs SERVICE=api)
	docker compose logs -f $(SERVICE)

docker-ps: ## List status and exposed ports of all containers
	docker compose ps

docker-clean: ## Stop containers and remove volumes (wipes database & qdrant data)
	docker compose down -v --remove-orphans

## 🧹 Maintenance Commands
clean: ## Remove temporary python cache files, .pyc, and test artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov
	@echo "✨ Cleaned all cache files and build artifacts."
