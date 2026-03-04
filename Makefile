.DEFAULT_GOAL := help

# ── Colors ───────────────────────────────────────────────
YELLOW := \033[1;33m
BLUE   := \033[0;34m
NC     := \033[0m

##@ Ayuda

help: ## Mostrar esta ayuda
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Setup

setup: ## Ejecutar setup.sh + git init
	@bash setup.sh
	@if [ ! -d .git ]; then git init; fi

##@ Docker

up: ## Levantar todos los servicios
	@docker compose up -d || echo "No services defined yet (see docker-compose.yml)"

down: ## Detener todos los servicios
	docker compose down

build: ## Reconstruir imágenes
	docker compose build

logs: ## Ver logs de todos los servicios
	docker compose logs -f

status: ## Mostrar estado de los servicios
	docker compose ps

clean: ## Detener servicios y eliminar volúmenes
	docker compose down -v

##@ Tests

test-back: ## Ejecutar tests del backend
	cd backend && uv run pytest
