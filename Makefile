.DEFAULT_GOAL := help
-include .env

# ── Colors ───────────────────────────────────────────────
YELLOW := \033[1;33m
BLUE   := \033[0;34m
NC     := \033[0m

##@ Help

help: ## Show this help
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Setup

setup: ## Run setup.sh + git init
	@bash setup.sh
	@if [ ! -d .git ]; then git init; fi

##@ Docker

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Rebuild images
	docker compose build

logs: ## View logs for all services
	docker compose logs -f

status: ## Show services status
	docker compose ps

clean: ## Stop services and remove volumes
	docker compose down -v

##@ Database

db-migrate: ## Run Alembic migrations
	cd backend && DATABASE_URL="postgresql+asyncpg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost:$(POSTGRES_PORT)/$(POSTGRES_DB)" uv run alembic upgrade head

db-revision: ## Create new migration (usage: make db-revision MSG="description")
	cd backend && DATABASE_URL="postgresql+asyncpg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost:$(POSTGRES_PORT)/$(POSTGRES_DB)" uv run alembic revision --autogenerate -m "$(MSG)"

db-admin: ## Show pgAdmin connection info
	@echo "pgAdmin: http://localhost:$(PGADMIN_PORT)"
	@echo "Email: $(PGADMIN_EMAIL)"
	@echo "Password: $(PGADMIN_PASSWORD)"

##@ Tests

test-back: ## Run backend tests
	cd backend && uv run pytest

test-front: ## Run frontend tests
	cd frontend && npm run test:ci

test: test-back test-front ## Run all tests
