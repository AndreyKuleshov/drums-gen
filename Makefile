.DEFAULT_GOAL := help

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 5173

.PHONY: help install install-backend install-frontend \
        dev dev-backend dev-frontend \
        test test-backend test-frontend \
        lint lint-backend lint-frontend \
        check clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## ---------- install ----------

install: install-backend install-frontend ## Install backend + frontend deps

install-backend: ## Sync backend deps (uv)
	cd $(BACKEND_DIR) && uv sync

install-frontend: ## Install frontend deps (npm)
	cd $(FRONTEND_DIR) && npm install

## ---------- run (dev) ----------

dev: ## Run backend + frontend together (Ctrl-C stops both)
	@echo "Backend  -> http://localhost:$(BACKEND_PORT)"
	@echo "Frontend -> http://localhost:$(FRONTEND_PORT)"
	@trap 'kill 0' INT TERM; \
	( cd $(BACKEND_DIR) && uv run uvicorn drumgen.api:app --reload --port $(BACKEND_PORT) ) & \
	( cd $(FRONTEND_DIR) && VITE_API_BASE=http://localhost:$(BACKEND_PORT) npm run dev -- --port $(FRONTEND_PORT) ) & \
	wait

dev-backend: ## Run only the backend API (uvicorn, autoreload)
	cd $(BACKEND_DIR) && uv run uvicorn drumgen.api:app --reload --port $(BACKEND_PORT)

dev-frontend: ## Run only the frontend (vite dev server); set BACKEND_PORT to point it at the API
	cd $(FRONTEND_DIR) && VITE_API_BASE=http://localhost:$(BACKEND_PORT) npm run dev -- --port $(FRONTEND_PORT)

## ---------- test ----------

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests (pytest)
	cd $(BACKEND_DIR) && uv run pytest -q

test-frontend: ## Run frontend tests (vitest)
	cd $(FRONTEND_DIR) && npm run test

## ---------- lint / typecheck ----------

lint: lint-backend lint-frontend ## Lint + typecheck everything

lint-backend: ## ruff + pyright (strict)
	cd $(BACKEND_DIR) && uv run ruff check . && uv run ruff format --check . && uv run pyright

lint-frontend: ## vue-tsc typecheck
	cd $(FRONTEND_DIR) && npm run typecheck

## ---------- combined ----------

check: lint test ## Run all quality gates (lint + tests)

clean: ## Remove build/cache artifacts
	rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/*.tsbuildinfo
	find $(BACKEND_DIR) -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.ruff_cache
